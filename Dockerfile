FROM mgorny/gentoo-python
WORKDIR /gpyutils
COPY . /gpyutils
RUN ["tox"]
