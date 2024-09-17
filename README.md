# AI-Analytics-BackEnd

AI Analytics BackEnd

## Features

-   Python FastAPI backend.
-   MongoDB database.
-   Authentication
-   Deployment

## Using the applicaiton

To use the application, follow the outlined steps:

1. Clone this repository and create a virtual environment in it:

```console
$ python3 -m venv venv
```

2. Install the modules listed in the `requirements.txt` file:

```console
(venv)$ pip3 install -r requirements.txt
```

3. You also need to start your mongodb instance either locally or on Docker as well as create a `.env` file. See the `.env.sample` for configurations.

    Example for running locally MongoDB at port 27017:

    ```console
    cp .env.sample .env
    ```

4. Start the application:

```console
python3 main.py
```

The starter listens on port 8000 on address [0.0.0.0](0.0.0.0:8080).

![FastAPI-MongoDB](doc.png)

## Testing

To run the tests, run the following command:

```console
(venv)$ pytest
```

You can also write your own tests in the `tests` directory.  
The test follow by the official support [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/), [pytest](https://docs.pytest.org/en/stable/), [anyio](https://anyio.readthedocs.io/en/stable/) for async testing application.

## Deployment

This application can be deployed on any PaaS such as [Heroku](https://heroku.com) or [Okteto](https://okteto) and any other cloud service provider.

## Contributing ?

Fork the repo, make changes and send a PR. We'll review it together!
