import hudson.model.*

def q = Jenkins.instance.queue

q.items.each { q.cancel(it.task) }
