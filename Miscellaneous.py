from flask import Flask, jsonify
import json
app = Flask(__name__)

file = {
    "owner_name": 123,
    "pass": 123
}

@app.route('/test')
def test():
    jsoni =  jsonify(file)
    
    f = json.loads(jsoni)

    print(f)
    
    
    return json

if __name__ == "__main__":
    print(test())
    app.run(debug=True)