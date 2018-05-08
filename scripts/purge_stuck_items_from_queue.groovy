import hudson.model.*

def q = Jenkins.instance.queue
long now = new Date().getTime()

q.items.findAll { 
        (now - it.getInQueueSince())/60000 > 90
    }.each { 
        q.cancel(it.task) 
    }
