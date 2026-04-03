FROM openjdk:22-jdk-slim

RUN apt-get update && apt-get install -y maven curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir /app/notes /app/files

COPY pom.xml /app
RUN mvn dependency:go-offline

COPY src /app/src


RUN mvn clean package -DskipTests

CMD java -jar target/JerkNotes-0.0.1-SNAPSHOT.jar & \
    echo "Waiting for Spring application to be ready..." && \
    until curl -s -o /dev/null -w "%{http_code}" http://localhost:1338/auth/login | grep -q "200"; do \
        echo "Spring app is not ready yet. Retrying..."; \
        sleep 5; \
    done && \
    echo "Spring application is ready! Running script..." && \
    wait;
