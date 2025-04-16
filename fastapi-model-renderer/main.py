import pickle
from fastapi import FastAPI

app = FastAPI()
model = pickle.load(open("model.pkl", 'rb'))


@app.get("/")
def predict(number):
    number = int(number)

    # Model input must be 2D. Therefore, we convert the number we received to a 2-dimensional array.
    model_input = [[number]]

    result = model.predict(model_input)

    # The model result is like this: [[30]]. We need to call result[0][0] for get the number
    result = result[0][0]

    return {"result": result}