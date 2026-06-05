import numpy as np
from sklearn.linear_model import LinearRegression


def forecast(values, steps=6):
    """
    Simple ML forecasting using Linear Regression
    """

    if len(values) < 3:
        return []

    X = np.array(range(len(values))).reshape(-1, 1)
    y = np.array(values)

    model = LinearRegression()
    model.fit(X, y)

    future_X = np.array(range(len(values), len(values) + steps)).reshape(-1, 1)
    predictions = model.predict(future_X)

    return predictions.tolist()