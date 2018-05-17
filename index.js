'use strict'

const {promisify} = require('util')
const execFile = promisify(require('child_process').execFile)
const fs = require('fs-extra')
const request = require('request-promise-native')
const tmp = require('tmp-promise')
const path = require('path')
const _ = require('lodash')

const  MODEL_BASE_PATH = process.env.MODEL_BASE_PATH || './sample_data'

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

  rows.push(headings.join(','))

  _.forEach(_.first(columns), (timestamp, index) => {
    rows.push(_.map(columns, (c) => {
      return c[index]
    }).join(','))
  })

  rows.splice(1,0,rows[1])

  return rows.join('\n')
}

async function main () {
  try {
    // const {stdout, stderr} = await execFile('ls', ['-lisa'])
    const result = await request({
      url: 'http://leela.msaas.me:22345/workToDo/pull',
      method: 'post',
      json: true,
      resolveWithFullResponse: true
    })

    console.log(result)

    const id = result.body.task['model-instance-id']
    const input = result.body.task['input']

    console.log('id', id)
    
    // create model file
    const modelFile = await tmp.file()
    const modelFileContent = await fs.readFile(path.join(MODEL_BASE_PATH, id, 'model_instance.fmu'), {encoding: null})
    await fs.writeFile(modelFile.path, modelFileContent, {encoding: null})

    // create tmp file for input
    const inputFile = await tmp.file()
    const csv = convertTimeseriesArrayToCsv(input)
    
    await fs.writeFile(inputFile.path, csv, {
      encoding: 'utf8'
    })


    // create tmp file for output
    const outputFile = await tmp.file()

    // to something here
    const {
      stdout,
      stderr
    } = await execFile('pipenv', ['run', 'fmpy', 'simulate', modelFile.path, '--output-file=' + outputFile.path, '--input-file=' + inputFile.path])

    const output = await fs.readFile(outputFile.path, {encoding: 'utf8'})
    
    console.log('output')
    console.log(output)

    outputFile.cleanup()
    inputFile.cleanup()
    modelFile.cleanup()
    

  } catch (error) {
    console.log('error', error)
  }

}

main()
