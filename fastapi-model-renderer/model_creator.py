from sklearn.linear_model import LinearRegression

X = [[1], [2], [3], [4], [5]]
y = [[2], [4], [6], [8], [10]]

model = LinearRegression()
model.fit(X, y)

import pickle
pickle.dump(model, open('model.pkl', 'wb'))