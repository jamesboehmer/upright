### Building a runtime docker image:

`docker build -f Dockerfile -t upright-dev  .`

### Building a runtime docker image with pycharm debug extensions:

Be sure to copy your pycharm's helpers directory into the source directory
`docker build -f Dockerfile.pycharm -t upright-pycharm .`

### Running the bot in a container

`docker run -v /Users/james.boehmer/src/upright/upright:/upright -e SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN -e SLACK_BOT_ID=$SLACK_BOT_ID -it upright-dev python3 upright/bot.py`