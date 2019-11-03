# personal_learning_paths
#### Project by the Humans 2.0 hackathon group Jagged Edge

Our project consists of two primary elements:
- Python webserver component to handle data processing 
- JavaScript extension component to interface with the web browser neatly

There is an optional node.js component in `bci/` which connects to a BCI device if available to measure user focus and concentration. There is no need to install this component if you are not using the hardware.

### How to ready your Python 3 environment

Quickest way to get you started is to run
`pip install -r requirements.txt`
(depending on your system/environment configuration, may need to change `pip` for `pip3`)

This will install our Python dependencies for your configured Python environment. If you struggle with permission errors, or 'access denied', add `--user` to your command i.e. `pip install --user -r requirements.txt`

Once you've installed the pre-requisites to your environment, you should be able to run the command `flask run` inside the directory. This will start the web server locally which the Tampermonkey script will report to.

Note that the system depends on the Tensorflow deep learning library, but is not compatible with the just-released 2.0 version. You may need to manually install an earlier version of Tensorflow with:

`pip install tensorflow==1.15`

### Configuring your Browser

We're using a browser extension called '_Tampermonkey_' to be able to interface directly with the browser's contents without needing to go so far as to make our own extension. 

The extension can be installed for [Chrome](https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo) or [Firefox](https://addons.mozilla.org/en-US/firefox/addon/tampermonkey/) 
(as a note, we've tested mainly with Chrome 77.0)

Install the extension, and you'll find the extension usually next to your address bar. Click it, and hit 'Create a new script'.
You'll clear all the content it starts you with, and open up [YTMonitor.user.js](/YTMonitor.user.js) found in the repo. 

Copy + Paste into there (you may be able to drag and drop directly into the edit window), save, and so long as you keep Tampermonkey and the script enabled, you're good to go.
