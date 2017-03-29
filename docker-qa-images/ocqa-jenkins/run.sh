docker run -d -p 8080:8080 -v $PWD/jenkins:/var/jenkins_home -v /var/run/docker.sock:/var/run/docker.sock -t ocqa-jenkins
