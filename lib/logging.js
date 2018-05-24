const os = require('os')
const _ = require('lodash')

function createLogger(name) {
  const logTemplate = {
    name: name,
    hostname: os.hostname(),
    pid: process.pid,
  }

  function log(level, msg, code, err) {
    const entry = JSON.parse(JSON.stringify(logTemplate))
    entry.level = level
    entry.msg = msg
    entry.code = code

    if (_.isError(err)) {
      entry.err = err.toString()
    }
    entry.time = new Date()

    console.log(JSON.stringify(entry))
  }

  function fatal(msg, code, err) {
    log(60, msg, code, err)
  }

  function error(msg, code, err) {
    log(50, msg, code, err)
  }

  function warn(msg, code, err) {
    log(40, msg, code, err)
  }

  function info(msg, code, err) {
    log(30, msg, code, err)
  }

  function debug(msg, code, err) {
    log(20, msg, code, err)
  }

  function trace(msg, code, err) {
    log(10, msg, code, err)
  }

  const lognInstance = {
    log: log,
    fatal: fatal,
    error: error,
    warn: warn,
    info: info,
    debug: debug,
    trace: trace
  }

  return lognInstance
}

exports.createLogger = createLogger