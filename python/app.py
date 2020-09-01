from flask import Flask, request, jsonify
import sqlite3
import json
import re # regular expressions
from pprint import pprint

from flask_restful import abort

app = Flask(__name__)
DBPATH = "../database.db"

@app.route("/messages", methods=["GET"])
def messages_route():
    """
    Return all the messages
    """

    with sqlite3.connect(DBPATH) as conn:
        messages_res = conn.execute("select body from messages")
        messages = [m[0] for m in messages_res]
        state_res = conn.execute("select * from state")
        states = state_res.fetchall()
        states_dict = dict(states)
        translated_messages = []

        def dashrepl(matchobj):
            if (matchobj.group(1) in states_dict):
                if (states_dict.get(matchobj.group(1))):
                    return states_dict.get(matchobj.group(1))
            else:
                return matchobj.group(2)

        for message in messages:
            translated_messages.append(re.sub('{([a-zA-Z0-9]+)\|([a-zA-Z0-9\!\?\'\"\s]*)}', dashrepl, message))

        return jsonify(list(translated_messages)), 200

@app.route("/search", methods=["POST"])
def search_route():
    """
    Search for answers!

    Accepts a 'query' as JSON post, returns the full answer.

    curl -d '{"query":"Star Trek"}' -H "Content-Type: application/json" -X POST http://localhost:5000/search
    """

    with sqlite3.connect(DBPATH) as conn:
        query = request.get_json().get("query")
        if not query:
            abort(400)

        def statement_condition_and_variables_builder(query):
            answersCondition = ""
            blocksCondition = ""
            words = query.split(" ")
            variable = []
            for word in words:
                answersCondition = answersCondition + "a.title like ? and "
                blocksCondition = blocksCondition + "json_extract( value, '$.body' ) like ? and "
                formatedWord = "%" + word + "%"
                variable.append(formatedWord)
            variables = []
            for i in range(2):
                variables = variables + variable

            statement = "select a.id, a.title, b.content from answers as a join blocks as b, json_each(json_array(b.content)) on a.id = b.answer_id where "
            answersCondition = "(" + answersCondition[:-5] + ")"
            blocksCondition = "(" + blocksCondition[:-5] + ")"
            statement = statement + "(" + answersCondition + " or " + blocksCondition + ")"
            return statement, variables


        statement, variables = statement_condition_and_variables_builder(query)
        res = conn.execute(statement, variables)

        answers = [{"id": r[0], "title": r[1], "content": json.loads(r[2])} for r in res]
        return jsonify(answers), 200


if __name__ == "__main__":
    app.run(debug=True)
