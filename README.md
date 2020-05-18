# trello-tracker
Retrieves lists and cards from a pre-defined Trello Board and generate an email from a template

## Usage

Copy `.trello-tracker.ini` to your `$HOME` and set it up accordingly.

Then you just need to run:
`python trello-tracker.py`


## How to get gte fields you will need in trello

1 - API Key

  Login into your trello account, then go to this URL : https://trello.com/app-key
  You will see the API key listed.


2 - Token

  Login into your trello account, then go to this URL : https://trello.com/app-key
  Next click in the 'Token' link. You will be asked to confirm your account and then in the botton, click the butto 'Allow'
  After that, you will see the token displayed.
  KEEP THAT WITH YOU ONLY !!

3 - BoardId
 
  Once logged into your account, go to 'Settings' option in the menu
  Then select the tab 'Configurations'  and then hit the button 'Export personal data'
  It will display a json with your personal data, including your boards, and its ID
 
