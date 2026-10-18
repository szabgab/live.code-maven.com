
* Use `uv run generate.py` to build the static web site.
* Embed the dependencies in the `generate.py` file.
* Run `black` after making changes. `uv run --with black black generate.py`

* JavaScript code is also in functions in the `static/js/live.js` file.

* On the topic pages show links to the calendar, LinkedIn, Facebook, and Telegram pages of the given topic taken from the configuration file. Add icons in-front of each link.
* For each topic, if there is a "text" field in the configuration then show that text (after markdown to html conversion) instead of the default text at the top of the page.

* Under "Earlier events and video recordings" show the list of earlier events. If there are no earlier events then show the text "No earlier events in this topic."
* Under "Schedule" show the list of future events. If there are no planned events then show "Currently there are no planned events in this topic. If you'd like to give a presentation look at the [CFP](/cfp) to understand what is needed and discuss it with Gabor."
