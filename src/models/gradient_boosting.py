import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_squared_error

df = pd.read_csv('data/combined/data_04.csv')

X = df.drop(columns=['Dollars Paid'])
y = df['Dollars Paid']

categorical_features = ['State', 'County']
ohe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
X_encoded = ohe.fit_transform(X[categorical_features])

X_encoded_df = pd.DataFrame(X_encoded, columns=ohe.get_feature_names_out(categorical_features))
X = X.drop(columns=categorical_features).reset_index(drop=True)
X = pd.concat([X, X_encoded_df], axis=1)

train = df[df['Year'] < df['Year'].max()]
test = df[df['Year'] == df['Year'].max()]

X_train = X.loc[train.index]
y_train = y.loc[train.index]
X_test = X.loc[test.index]
y_test = y.loc[test.index]

model = GradientBoostingRegressor(n_estimators=100, learning_rate=1, random_state=42, verbose=1)

print("Training model...")
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
print(f'Mean Squared Error: {mse}')