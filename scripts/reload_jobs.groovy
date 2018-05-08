import hudson.model.*

def allJobs = Jenkins.instance.allItems(Job.class)

allJobs.each { it.doReload() }

print "All jobs were reloaded"
