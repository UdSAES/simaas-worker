'use strict'

const {promisify} = require('util')
const execFile = promisify(require('child_process').execFile)
const fs = require('fs-extra')
const request = require('request-promise-native')
const tmp = require('tmp-promise')
const path = require('path')
const _ = require('lodash')

const  MODEL_BASE_PATH = process.env.MODEL_BASE_PATH || './sample_data'

const COLUMN_SEPARATOR = ','

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
  
  console.log(result)

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
  
}

async function main () {
  try {
    const result = await request({
      url: 'http://leela.msaas.me:22345/workToDo/pull',
      method: 'post',
      json: true,
      resolveWithFullResponse: true
    })

    const taskId = result.body.id
    const modelInstanceId = result.body.task['model-instance-id']
    const input = result.body.task['input']

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
    
    const outputTimeseriesArray = convertCsvToTimeseriesArray(output, modelInfo)

    const setResultResponse = request({
      url: 'http://127.0.0.1:22345/workToDo/results/' + taskId,
      method: 'post',
      json: true,
      resolveWithFullResponse: true,
      body: {
        error: null,
        result: outputTimeseriesArray
      }
    })

    // console.log(setResultResponse)

  } catch (error) {
    console.log('error', error)
  }

}

main()
