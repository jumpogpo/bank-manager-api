<p align="center">
  <a href="https://github.com/jumpogpo/bank-manager-api.git" target="blank"><img src="https://github.com/jumpogpo/bank-manager-api/blob/main/src/images/bank_logo.png?raw=true" width="200" height="200" alt="KPang Logo" /></a>
</p>

## 👋 Description
This project is a mock bank API, which utilizes FASTAPI for API development and MongoDB for data storage. It is deployed using Docker.

## 🧃 Preface

<p>This project is created to submit to the instructor for the Operating System course at King Mongkut's Institute of Technology Ladkrabang (KMITL). The task is to develop any service but it must be deployed using Docker.</p>

## 📝 How to use?

- Clone this project following the installation instructions.
- Setting the port in the Dockerfile and docker-compose.yaml file.
- Deploy the api.

## 📚 Installation

```bash
# Clone project
$ git clone https://github.com/jumpogpo/bank-manager-api.git

$ cd bank-manager-api
```

## 📺 Deploy the app

```bash
# Build the image
$ docker build . -t bank-manager-api

# Run the image
$ docker-compose up -d
```

## 🤝 Reference

- FastAPI - [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- MongoDB - [https://www.mongodb.com/](https://www.mongodb.com/)
- Docker - [https://www.docker.com/](https://www.docker.com/)