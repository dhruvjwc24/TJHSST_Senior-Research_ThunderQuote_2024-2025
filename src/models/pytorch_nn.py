import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import mean_squared_error
from torch.utils.data import DataLoader, TensorDataset

df = pd.read_csv('data/combined/data_04.csv')

X = df.drop(columns=['Dollars Paid'])
y = df['Dollars Paid'].values

categorical_features = ['State', 'County']
ohe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
X_encoded = ohe.fit_transform(X[categorical_features])
X_encoded_df = pd.DataFrame(X_encoded, columns=ohe.get_feature_names_out(categorical_features))

X = X.drop(columns=categorical_features).reset_index(drop=True)
X = pd.concat([X, X_encoded_df], axis=1)

train = df[df['Year'] < df['Year'].max()]
test = df[df['Year'] == df['Year'].max()]

X_train = X.loc[train.index].values
y_train = y[train.index]
X_test = X.loc[test.index].values
y_test = y[test.index]

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
y_train_tensor = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
X_test_tensor = torch.tensor(X_test, dtype=torch.float32)
y_test_tensor = torch.tensor(y_test, dtype=torch.float32).view(-1, 1)

dataset = TensorDataset(X_train_tensor, y_train_tensor)
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

class RegressionNN(nn.Module):
    def __init__(self, input_size):
        super(RegressionNN, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 32)
        self.fc4 = nn.Linear(32, 1)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.relu(self.fc3(x))
        x = self.fc4(x)
        return x

model = RegressionNN(X_train.shape[1])

criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

epochs = 50
print("Training model...")
for epoch in range(epochs):
    for batch_X, batch_y in dataloader:
        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()
    
    if (epoch + 1) % 10 == 0:
        print(f'Epoch {epoch+1}/{epochs}, Loss: {loss.item()}')

model.eval()
y_pred_tensor = model(X_test_tensor).detach().numpy().flatten()
mse = mean_squared_error(y_test, y_pred_tensor)
print(f'Mean Squared Error: {mse}')
