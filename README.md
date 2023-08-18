# 🦆 Quack to my data 🦆

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/gregwdata/quack_to_my_data?quickstart=1)

## 🤔 What is this?

This is a project meant to get hands-on with the concept of using an LLM to engage with a database.

It will use a local instance of 🦆 DuckDB to store some sample data sets. It will serve as a vehicle for exploring different approaches to guide the AI to produce correct and useful queries against the dataset.

Development will initially be centered around running in GitHub Codespaces.

![Screen capture of an example interaction. The user asks for example part names, then asks for total revenue associated with one of the part names. In both cases a Llama2 70B LLM generates SQL queries that provide the answer, then summarizes the final revenue number.](./assets/quack_part_revenue.gif)

## 🤨 Why do this?

After hearing so many discussions of and articles about LLMs where everyone points to a "talk-to-your-database" use case as some kind of self-evidently worthwhile example of what LLMs can do, it seemed worthwhile to learn more about it. 

How easy is it to implement yourself?

Does it actually benefit a non-technical user? I.E. do the questions input to the LLM need to be expressed in a way that maps one-to-one with SQL? ("What is the total number of sales I made to each customer in the midwest in the second quarter?") If you know SQL, it might be natural to state your question that way, but then you don't need an LLM getting between you and your data. What if a user asks "How were our numbers in the midwest market last quarter?" or tries to actually derive an *actionable* insight directly: "What machine is the worst-performing bottleneck in my factory?"

How well will a general-purpose model perform? Or will you need a model specifically trained on SQL tasks, like [NSQL](https://github.com/NumbersStationAI/NSQL) to get usable queries?

What are the limits of complexity that can be achieved? How many joins before the model can't keep up?

And is there any real **value** to something like this, other than being a novelty? Would it serve a useful purpose in fielding initial inquiries from non-SQL-fluent stakeholder? Can it help a technical analyst perform more efficiently?

The catalyst for action was listening to a couple podcast episodes in close succession: 

One was [Maxime Beauchemin on the MLOps Community Podcast](https://home.mlops.community/home/videos/treating-prompt-engineering-more-like-code) describe the approach to working with LLMs in a very clear and systematic way. Listening to him break down the process of approaching the development of LLM-based applications made it seem actually *doable*. I had a sense of where I could start and what to try.

The other was an episode of [Latent Space / The AI Breakdown](https://www.latent.space/p/breakdown), which included a duscussion of just how far along the Llama2 model was in capability. With a commercial-friendly license on such a powerful model, that one could run on ones own infrastructure, is there line of sight to using a model like Llama2 for real internal enterprise usage?

It sure seemed like a good time to take it for a spin and find out.

I'm hoping to build this in a way that serves as an example of "here's a way you could do it" (not here's how you *should* do it, of course) for anyone else curious about this in the same way I was. I want it to be accessible and easy for someone else to pick up and experiment with.

### 🦆 Why use DuckDB?

In a word: simplicity. In another word: performance.

I wanted to strip away the particulars of dealing with the database - Python connection APIs are available for nearly any database one might want to apply this approach to, so it's somewhat orthogonal to the purpose of this project which database is used.

DuckDB has the nice property that it runs inside the Python process the of the rest of the app, removing deployment and development headaches around managing a database instance.

For the purpose of exercising this LLM-SQL concept with a variety of different datasets and database structures, DuckDB makes it trivially simple to switch datasets on the fly by connecting to a different `.duckdb` file. Connection to remote-hosted files and cloud data stores is also easy.

And storage is efficient enough that I can include several `.duckdb` database files within this GitHub repository with enough data to make them interesting to work with, and not worry about file size.

Its SQL dialect inlcudes the vast majority of commands an LLM is likely to come up with while building queries. Both ANSI SQL concepts and convenience methods extending SQL used by many common databases work with DuckDB.

DuckDB is extremely fast for every analytics-focused use case where I've used it. Using it here would minimize latency in the iteration of LLM to database - we're spending enough time waiting for LLM API calls to return! Plus, its performance may help to compensate for poorly-optimized or unusual queries generated by the LLM.

## Features

⚡ Streamlit interface

🦆 Queries generated by the LLM are executed with DuckDB - modular and easy to add a new dataset!

📜 Easy to follow and customize prompt setup in `prompt_tools.py`, which prepare system and main prompts with instructions for model behavior and details of the structure of the data

🧵 Tooling for parsing model responses and acting on or iterating through actions that the model wants to take, including executing queries, are in `utils.py`

🔬 Additional database-specific prompts, with context about the data that may be useful to the model and details about relationships between tables, are specified in `db_specific_prompts.py`

🤖 `llama2_chatbot.py` is the main Streamlit app code

## Datasets

To add a new dataset:

* If needed, write a helper script in `./db_utils/`. The script should write the db as a `.duckdb` file to a subfolder of the `./db_files/` directory.

    * The subfolder should have a name in common with the database file

* Add a section to the `Makefile` to create the subfolder and run the script. If no script needed (data already prepared)

* In `db_specific_prompts` add an item to the dictionary matching the database name

### TPC-H 

A [TPC-H](https://www.tpc.org/tpch/) benchmark dataset is created using DuckDB's `tpch` extension. For now the scale factor used is `0.1` for speed of creation and keeping the database to a reasonable small size for development.

### LFU

This data set is from the [Ladle Furnace Unit](https://www.kaggle.com/datasets/yuriykatser/industrial-data-from-the-ladlefurnace-unit) dataset posted with CC0 license on Kaggle. It is data from 7 interrelated tables of data describing a steel melting process. The original goal of this dataset on Kaggle is to develop a prediction of temperature values over time. In this app, the model has been instructed to use the temperature table that does not have missing values unless otherwise specified.

This dataset was selected since working with it may require joins across the tables; however, the joins are fairly easy in most cases since all rows share a key representing the melt batch they are from. One challenging aspect is the mix of grains throughout the dataset. Llama2 has struggled with this in my initial trials. Some tables are one row per batch, while others have time series data. 

The `bulk` and `wire` tables, and their accompanying `_time` tables are particularly confusing for the model to work with, since they are very sparse and are organized by a column for each elemental constituent, with the times in the same location in a separate table. Perhaps better results would be achieved by first converting these tables to a long format for use by the model.

## Usage on Codespaces
Start Codespaces on this repository by clicking [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/gregwdata/quack_to_my_data?quickstart=1)
, or you can click on the Green code button on top right of the repo.

To run this app, you will need to have a [replicate](https://replicate.com/) API key. Once you've obtained it, there are three options for using it within the app in Codespaces:

* Following [these instructions](https://docs.github.com/en/codespaces/managing-your-codespaces/managing-encrypted-secrets-for-your-codespaces), you can securely store your API key as a secret within GitHub, tied to this repository. Be sure to name it `REPLICATE_API_TOKEN` so it is available in the codespace as an environment variable with the correct name.
    * Using this method, if you set up this secret before opening the repo in Codespaces, the App will work correctly right out of the box.
* In the `.env` file, uncomment the `REPLICATE_API_TOKEN` line, and add your API token there. `.env` is inlcuded in the `.gitignore` file, so this key will not be committed.
    * You will need to restart the app using `make run_app` after adding this the first time you start your Codepsace
* Manually add it as an environment variable with `export REPLICATE_API_TOKEN=<your token here>`
    * You will need to restart the app using `make run_app` after adding this the first time you start your Codepsace


When the app runs on startup or manually by running `make run_app` at the command line, the app should load within a preview browser inside the IDE. You can also click the `Ports` tab in the lower pane and the 🌐 icon that appears when you hover over the local address field to open it in its own browser tab.

## 🧠 Deep Thoughts

Recording a few reactions and observations here. May expand on them here or in separate write-ups.

### 🤯 It works!

The initial reaction is one of amazement the first few times you see it pick up on what you're asking for, generate a SQL query, and return and explain the results. All the more so when it iterates through a sequence of queries to get to an answer.

Eventually that wears off and you become more frustrated when it struggles with a query or gets stuck looping over the same output. Very much a Pareto-shaped problem where the first 80% of progress is easy, and a significant effort remains to get to a robust-feeling, consistent experience. I hope to see how far prompting techniques can take this, as well as different models.

That periodic rush of awe when the Llama2 70B model does something seemingly clever is enough to motiviate continuing to play with this.

### 🤷‍♀️🤷‍♂️ Who is this for?

I'm still not sure that there's a target audience for something like this. 

For the capabale data person, you can just directly write the query and answer your own questions yourself. Any query generated by the model, I'm still inclined to double check to confirm it's doing what I want. Can I come up with some examples of data sets and questions that are complex enough that checking a model-generated query and iterating through a round of questions is a significant enough speedup over just doing that myself?

For a non data-fluent end user, how can they be confident whether the result is correct? They aren't going to be able to directly look at the generated SQL and know. Perhaps there should be a step in the loop that requires the model to explain how the generated query works, in lay terms. But how will we ensure *that* is correct?

And will they be able to formulate a  question in a way that the model can correctly interpret it into the corresponding SQL query? I should find some volunteers to test this on.

### 👁 Watch model versions closely
When I first started attempting to use this with LLaMA 70B, the results were underwhelming. It didn't seem to respond to the direction from prompting reliably. During iterations on the initial development, I noticed there were several more recent [versions of the Llama 2 chat model on Replicate](https://replicate.com/replicate/llama-2-70b-chat/versions) than the one used in the `.env_template` from the original A16Z repository I started with. Results improved significantly after switching to the latest version of the Replicate model.  

### 🚰 Leakage?

On initial trials of coaxing Llama2 to be useful by adjusting the prompts, it was easier to achieve occasionally-satisfying results on the TPC-H dataset than with queries on LFU. Is there some amount of TPC-H-related content in the massive amount of data that Llama2 was trained on? Probably.

### ⛓ How helpful is LangChain?
While trying different initial prompts and making little progress (likely due to the above issue), I decided to see if I could get better results with LangChain. Why not start with a higher level of abstraction where someone else has already implemented best practices?

👍 It was helpful to observe the patterns used in prompting, agent modeling, and "tool" use employed by Langchain. It's a great reference point for best practices. I incorporated a number of things I picked up from Langchain's SQL prompting in the custom prompt tooling I ended up using.

👎 The API and design of Langchain makes it pretty tough to customize. I couldn't find any obvious way to make some of the basic modifications to prompts, cleanup of responses (e.g. regex operations on the response that I wanted to run on the SQL query to prevent the more common syntax errors), or behavior that a model can invoke. I ended with a combination of monkey-patching some functionality, along with copying and customizing whole class definitions from the Langchain repository, in order to implement some of the changes I wanted to make.

Another noteworthy experience - though not a complaint, rather in case someone reading this finds it useful - is I attempted to use Langchain shortly after [the experimental features were split off in the repo](https://github.com/langchain-ai/langchain/discussions/8043). I started following the example of the [SQL Database Agent](https://python.langchain.com/docs/integrations/toolkits/sql_database), but after finding that underwhelming, and seeing references to `SQLDatabaseChain` on various tutorials for using Langchain, I wanted to switch to that. But all of the available tutorials dated from at least a couple weeks prior, before it had been moved to the `langchain_experimental` Python package. It took some sleuthing through the docs and modified repository structure, but I was able to piece back together how to use it. The original [Agent method](https://github.com/gregwdata/quack_to_my_data/tree/try_langchain) and [SQLDatabaseChain](https://github.com/gregwdata/quack_to_my_data/tree/try_langchain_w_SQL_Database_Chain) implementation branches are still available in this repository for reference, though they are not actively developed.

In the interest of rapid iteration and more complete control the behavior of the LLM interaction, I went back to the manually-built prompting-parsing loop that is presently implemented in the `main` branch.

## Authors

Built by Greg Wilson [![Linkedin](https://i.stack.imgur.com/gVE0j.png)](https://www.linkedin.com/in/greg-wilson-6212572/)

## Version

0.0.1 (initial setup) August 2023

## Plans

* Add more datasets
* Instrument with logging to store prompts, results, and configuration details to be more systematic about development
   * Perhaps try [promptimize](https://github.com/preset-io/promptimize)
* Try out different prompting approaches
* Try out different models
   * Inlcude options with a free API for demoing 
* Showcase good / bad examples
* Add "capabilites" to the model. E.G. specifying plots

## Contributing

This project is under development. Contributions are welcome!

## License

- This repo was started from https://github.com/a16z-infra/llama2-chatbot, which is published with an Apache 2.0 License
- Modifications made as part of derivative work in this project are licensed MIT

## Disclaimer

This is an experimental version of the app. Use at your own risk. While the app has been tested, the authors hold no liability for any kind of losses arising out of using this application. 

## Resources

- [Streamlit Cheat Sheet](https://docs.streamlit.io/library/cheatsheet)
- [GitHub to deploy LLaMA2 on Replicate](https://github.com/a16z-infra/cog-llama-template)
