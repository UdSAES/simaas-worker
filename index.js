'use strict'

const {promisify} = require('util')
const execFile = promisify(require('child_process').execFile)
const fs = require('fs-extra')
const request = require('request-promise-native')
const tmp = require('tmp-promise')
const path = require('path')
const _ = require('lodash')
const delay = require('delay')
const bunyan = require('bunyan')
const logging = require('./lib/logging')

const URL_QUEUE = process.env.URL_QUEUE || 'http://localhost:22345'
const MODEL_BASE_PATH = process.env.MODEL_BASE_PATH || './sample_data'
const WAIT_TIME = process.env.WAIT_TIME || 50

const COLUMN_SEPARATOR = ','
const EVENTS = {
  TASK_HANDLED_SUCCESSFULLY: 31001,
  UNEXPECTED_STATUS_CODE: 50001,
  TASK_ID_INVALID: 50002,
  TASK_INVALID: 50003,
  SIMULATION_FAILED: 50004,
  SET_RESULT_FAILED: 50005,
  TASK_NOT_AVAILABLE_ANYMORE: 50006,
  PULLING_TASK_FAILED: 50007,
}

const log = logging.createLogger('simaas_worker')

function createError(message, code) {
  const error = new Error(message)
  error.code = code
  return error
}

function parseFMPYInfoOutput (infoOutput) {
  const VARIABLE_SECTION_HEADER = 'Variables (input, output)'

  infoOutput = infoOutput.replace(/\r\n/g, '\n')
  const lines = infoOutput.split('\n')

  const variableDefinitions = []
  let variableDefinitionState = 0
  _.forEach(lines, (line) => {
    if (variableDefinitionState === 0 && line === VARIABLE_SECTION_HEADER) {
      variableDefinitionState = 1
      return
    }

    if (variableDefinitionState === 1 && line === '') {
      variableDefinitionState = 2
      return
    }

    if (variableDefinitionState === 2 && line === '') {
      variableDefinitionState = 3
      return false
    }

    if (variableDefinitionState === 2) {
      const variableDefinition = {
        name: _.trimEnd(line.substr(0, 19)),
        causality: _.trimEnd(line.substr(20, 10)),
        startValue: parseFloat(_.trimStart(line.substr(30, 23))),
        unit: _.trimEnd(line.substr(56, 8)),
        description: _.trimEnd(line.substr(65))
      }

      variableDefinitions.push(variableDefinition)
    }
  })

  const result = {
    variableDefinitions: variableDefinitions
  }

  return result
}

function convertTimeseriesArrayToCsv (timeseriesArray) {
  const columns = _.map(timeseriesArray, (timeseries) => {
    return _.map(timeseries.timeseries, (te) => {
      return te.value
    })
  })



  const timestamps = _.map(_.first(timeseriesArray).timeseries, (te) => {
    return te.timestamp
  })

  columns.splice(0, 0, timestamps)
  const rows = []

  // create headers
  const headings = ['"time"']
  _.forEach(timeseriesArray, (timeseries) => {
    headings.push('"' + timeseries.label + '"')
  })

  rows.push(headings.join(COLUMN_SEPARATOR))

  _.forEach(_.first(columns), (timestamp, index) => {
    rows.push(_.map(columns, (c) => {
      return c[index]
    }).join(COLUMN_SEPARATOR))
  })

  rows.splice(1,0,rows[1])

  return rows.join('\n')
}

function convertCsvToTimeseriesArray (csv, modelInfo) {
  csv = csv.replace(/\r\n/g, '\n')
  const lines = csv.split('\n')

  const headings = []
  const columns = []
  _.forEach(lines, (line, rowIndex) => {
    _.forEach(line.split(COLUMN_SEPARATOR), (valueString, columnIndex) => {
      if (rowIndex === 0) {
        headings.push(valueString.replace(/"/g, ''))
        return
      }

      columns[columnIndex].push(parseFloat(valueString))
    })

    if (rowIndex === 0) {
      _.forEach(headings, () => {
        columns.push([])
      })
    }
  })

  const timeseriesArray = []
  _.forEach(headings, (heading, columnIndex) => {
    if (columnIndex === 0) {
      return
    }
    const timeseriesItem = {}
    timeseriesItem.label = heading
    timeseriesItem.unit = _.find(modelInfo.variableDefinitions, (variableDefinition) => {
      return variableDefinition.name === heading
    }).unit


    timeseriesItem.timeseries = _.map(columns[columnIndex], (value, rowIndex) => {
      return {timestamp: columns[0][rowIndex], value: value}
    })

    timeseriesArray.push(timeseriesItem)
  })

  return timeseriesArray
}

async function processSimulationTask(task) {
  const modelInstanceId = task['model-instance-id']
  const input = task['input']

  // create model file
  const modelFile = await tmp.file()
  const modelFileContent = await fs.readFile(path.join(MODEL_BASE_PATH, modelInstanceId, 'model_instance.fmu'), {
    encoding: null
  })
  await fs.writeFile(modelFile.path, modelFileContent, {encoding: null})

  // create tmp file for input
  const inputFile = await tmp.file()
  const csv = convertTimeseriesArrayToCsv(input)

  await fs.writeFile(inputFile.path, csv, {
    encoding: 'utf8'
  })

  // create tmp file for output
  const outputFile = await tmp.file()

  // get info about fmu
  const infoResult = await execFile('pipenv', ['run', 'fmpy', 'info', modelFile.path])
  const modelInfo = parseFMPYInfoOutput(infoResult.stdout)

  // run simulation
  const {
    stdout,
    stderr
  } = await execFile('pipenv', ['run', 'fmpy', 'simulate', modelFile.path, '--output-file=' + outputFile.path, '--input-file=' + inputFile.path])

  const output = await fs.readFile(outputFile.path, {encoding: 'utf8'})

  outputFile.cleanup()
  inputFile.cleanup()
  modelFile.cleanup()

  return { output: output, modelInfo: modelInfo };
}

async function main () {
  while (true) {
    await delay(WAIT_TIME)
    let pullTaskResult = null
    
    // pull task
    try {
      pullTaskResult = await request({
        url: URL_QUEUE + '/tasks/_pull',
        method: 'post',
        json: true,
        resolveWithFullResponse: true
      })
    } catch (error) {
      // something went wrong
      log.error('pulling a task failed', EVENTS.PULLING_TASK_FAILED, error)
      continue
    }

    
    // no item available
    if (pullTaskResult.statusCode === 204) {
      continue
    }
    
    if (pullTaskResult.statusCode !== 200) {
      // unexpected status code
      log.error('unexpected status code for pulling task', EVENTS.UNEXPECTED_STATUS_CODE, new Error('' + pullTaskResult.statusCode))
      continue
    }
    
    log.info('task pulled')
    const taskId = _.get(pullTaskResult, ['body', 'id'])
    const task = _.get(pullTaskResult, ['body', 'task'])

    // taskId invalid
    if (!_.isString(taskId)) {
      log.error('invalid taskId', EVENTS.TASK_ID_INVALID)
      continue
    }
    
    // task invalid
    if (!_.isPlainObject(task)) {
      log.error('invalid task', EVENTS.TASK_INVALID)
      continue
    }

    let simulationResult = null
    try {
      simulationResult = await processSimulationTask(task)
    } catch (error) {
      log.error('simulation failed', EVENTS.SIMULATION_FAILED, error)
      continue
    }

    const outputTimeseriesArray = convertCsvToTimeseriesArray(simulationResult.output, simulationResult.modelInfo)

    let setResultResponse = null
    try {
      setResultResponse = await request({
        url: URL_QUEUE + '/tasks/' + taskId + '/result',
        method: 'post',
        json: true,
        resolveWithFullResponse: true,
        body: {
          error: null,
          result: outputTimeseriesArray
        }
      })
    } catch (error) {
      log.error('set result failed', EVENTS.SET_RESULT_FAILED, error)
      continue
    }

    // task not available anymore
    if (setResultResponse.statusCode === 404) {
      log.error('task not available anymore', EVENTS.TASK_NOT_AVAILABLE_ANYMORE)
      continue
    }

    if (setResultResponse.statusCode !== 200) {
      log.error('unexpected status code for set result', EVENTS.UNEXPECTED_STATUS_CODE, new Error('' + setResultResponse.statusCode))
      continue
    }

    log.info('successfull run', EVENTS.TASK_HANDLED_SUCCESSFULLY)
    // everything is fine
  }
}

main()
