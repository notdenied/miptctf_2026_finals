FROM golang:1.24-alpine AS builder

WORKDIR /app

RUN apk add --no-cache gcc musl-dev

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=1 GOOS=linux go build -o s3service cmd/server/main.go

FROM alpine:latest

RUN apk --no-cache add ca-certificates libc6-compat

WORKDIR /app

COPY --from=builder /app/s3service .

RUN adduser -D -u 1000 appuser && \
    mkdir -p /data/storage && \
    chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8080

CMD ["./s3service"]

