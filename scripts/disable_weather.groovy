// This script removes health checks for Folders
// Inspired by:
// https://support.cloudbees.com/hc/en-us/articles/216973327-How-to-disable-the-weather-column-to-resolve-instance-slowness-

def healthMetric = null
try {
 healthMetric = Class.forName( "com.cloudbees.hudson.plugins.folder.health.ProjectEnabledHealthMetric")
} catch( ClassNotFoundException e ) {
 //plugin isn't installed
}


def folders = Jenkins.instance.getAllItems(com.cloudbees.hudson.plugins.folder.Folder.class)
folders.each{ folder ->
  folder.healthMetrics.each{ metric ->
    if (!metric.getClass().equals(healthMetric)) {
      println "Removing ${metric.class.simpleName} from ${folder.name}"
      folder.healthMetrics.remove(metric)
      folder.save()
    }
  }
}
return null
