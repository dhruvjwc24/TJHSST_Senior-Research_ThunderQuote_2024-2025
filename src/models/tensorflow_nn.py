import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
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

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

model = tf.keras.Sequential([
    tf.keras.layers.Dense(128, activation='relu', input_shape=(X_train.shape[1],)),
    tf.keras.layers.Dense(64, activation='relu'),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(1)
])

model.compile(optimizer='adam', loss='mse', metrics=['mse'])

print("Training model...")
model.fit(X_train, y_train, epochs=50, batch_size=32, validation_split=0.2, verbose=1)

y_pred = model.predict(X_test).flatten()
mse = mean_squared_error(y_test, y_pred)
print(f'Mean Squared Error: {mse}')
