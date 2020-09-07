from flask import Flask, request, jsonify
import sqlite3
import json
import re  # regular expressions
from pprint import pprint
from collections import defaultdict

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

        def search_answers(title, word):
            if re.search(rf"\b{word}\b", title, re.IGNORECASE):
                return True

        """
        to extract all the values of the nested json 
        """
        def search_Blocks(object, word, flag):
            if not flag:
                if isinstance(object, dict):
                    for k, v in object.items():
                        if isinstance(v, list):
                            if search_Blocks(v, word, False):
                                return True
                        elif isinstance(v, str):
                            if k != 'type':
                                if re.search(rf"\b{word}\b", v, re.IGNORECASE):
                                    return True

                elif isinstance(object, list):
                    for item in object:
                        if search_Blocks(item, word, False):
                            return True
            else:
                return True

        statement = "select a.id, a.title, b.content from answers as a join blocks as b on a.id = b.answer_id"
        res = conn.execute(statement)
        answers = [{"id": r[0], "title": r[1], "content": json.loads(r[2])} for r in res]
        words = query.split(" ")
        results = []

        """
        In each row, for each word of the query, search in answers and blocks
        validate if all the words have been found in either answers or blocks 
        """
        for answer in answers:
            dword = defaultdict(lambda: 0)
            for word in words:
                if search_answers(answer['title'], word):
                    dword[word] = 1
                if search_Blocks(answer['content'], word, False):
                    dword[word] = 1
            dword_values = [dword[word] for word in words]
            if (min(dword_values)) > 0:
                results.append(answer)

        return jsonify(results), 200


if __name__ == "__main__":
    app.run(debug=True)
