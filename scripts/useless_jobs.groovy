import groovy.time.TimeCategory

use ( TimeCategory ) {
  // e.g. find jobs not run in last 3 months
  sometimeago = (new Date() - 3.months)
}

jobs = Jenkins.instance.getAllItems()

int total = 0
int useless = 0

jobs.each { j ->
  if (j instanceof com.cloudbees.hudson.plugins.folder.Folder) { return }

  total += 1

  lastbuild = j.getLastBuild()
  if (lastbuild == null) {
    println j.fullName + '  => no builds at all'
    useless += 1
    return
  }

  if (lastbuild.timestamp.getTime() < sometimeago) {
    useless += 1
    println j.fullName + '  => last build was ' + lastbuild.timestampString + ' ago'
  }
}

println ""
println "Were not executed in last 3 months: " + useless
println "Total number of jobs: " + total
