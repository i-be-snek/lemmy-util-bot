# https://git.walbeck.it/walbeck-it/docker-python-poetry
FROM mwalbeck/python-poetry:1.6.1-3.9

RUN mkdir src tests data

COPY main.py poetry.lock pyproject.toml .env /
COPY tests/* tests
COPY src/* src
COPY data/* data

RUN poetry config virtualenvs.create false && poetry install --only=main,test --no-interaction --no-ansi
RUN poetry run pytest tests/
CMD ["poetry", "run", "python3", "main.py"]
