"""
Lead-time model - can machine learning beat the simple averages?
The tracker predicts each stage with the typical (median) time for that part.
This tests whether a linear regression that ALSO knows how busy each stage was
(the queue when the part arrived) predicts better, on records it has never seen.
"""

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

HISTORY_FILE = "Aero_Parts_History.xlsx"
STAGES = ["Design", "Machining", "Inspection", "Model Fit"]
N_TESTS = 20   # how many different random hold-back sets to test on


def make_features(hist):
    """Turn each record into numbers the model can use."""
    # one column per part-and-stage combination: 1 if it's this one, 0 if not
    X = pd.get_dummies(hist["Part Name"] + " | " + hist["Stage"], dtype=float)
    # how many parts were already waiting, kept separate for each stage
    for s in STAGES:
        X["Queue at " + s] = hist["Queue On Entry"] * (hist["Stage"] == s)
    return X


def one_test(hist, X, y, seed):
    """Hold back 20% of records, train on the rest, return both methods' errors."""
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed)
    train, test = hist.loc[X_train.index], hist.loc[X_test.index]

    # 1) simple method: typical (median) days for that part at that stage
    medians = train.groupby(["Part Name", "Stage"])["Days Taken"].median()
    simple_pred = [medians[(p, s)] for p, s in zip(test["Part Name"], test["Stage"])]

    # 2) machine learning: linear regression that also knows the queue
    model = LinearRegression(fit_intercept=False)
    model.fit(X_train, y_train)
    ml_pred = model.predict(X_test)

    return mean_absolute_error(y_test, simple_pred), mean_absolute_error(y_test, ml_pred)


def main():
    hist = pd.read_excel(HISTORY_FILE, sheet_name="History")
    X = make_features(hist)
    y = hist["Days Taken"]

    # one test can be lucky or unlucky, so repeat with different hold-back sets
    results = pd.DataFrame([one_test(hist, X, y, seed) for seed in range(N_TESTS)],
                           columns=["Simple", "ML"])
    ml_wins = (results["ML"] < results["Simple"]).sum()

    print(f"Average error over {N_TESTS} tests on records each model never saw:")
    print(f"  Simple averages: off by {results['Simple'].mean():.2f} days")
    print(f"  ML model:        off by {results['ML'].mean():.2f} days")
    print(f"  ML was more accurate in {ml_wins} of {N_TESTS} tests")

    # train once on everything to see what it learned about queues
    model = LinearRegression(fit_intercept=False).fit(X, y)
    coefs = pd.Series(model.coef_, index=X.columns)
    print("\nWhat the model learned about queues:")
    for s in STAGES:
        print(f"  each extra part waiting at {s:<10} adds {coefs['Queue at ' + s]:.2f} days")


if __name__ == "__main__":
    main()
