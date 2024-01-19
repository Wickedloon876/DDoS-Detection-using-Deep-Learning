# -*- coding: utf-8 -*-
"""DDoS Detection CNN Model.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Y4OvNFFIXGRBKHSQYkIL9Exm4GQX8vSX
"""

#importing Python libraries needed
import tensorflow as tf
from tensorflow import keras
import IPython
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

!pip install -U keras-tuner
import kerastuner as kt

#mounting Google Drive to access the datasets
from google.colab import drive
drive.mount('/content/drive')

#accessing the datasets to build a dataframe
df1 = pd.read_csv("/content/drive/MyDrive/Colab Notebooks/data/Portmap.csv")
df2 = pd.read_csv("/content/drive/MyDrive/Colab Notebooks/data/UDPLag.csv")

"""**Using Combined Dataset containing both Portmap and UDPLag Dataset**"""

df = pd.concat([df1, df2], axis=0)

df.head(5)

df.shape #shape of the combined dataset

df[' Label'].value_counts() #number of each attack

df[' Label'].hist() #visual representation using histogram
plt.xlabel("Traffic Type")
plt.ylabel("Count")

"""**DATA PRE-PROCESSING: DROPPING VALUES** """

df = df.replace([np.inf, -np.inf], np.nan) #replacing abnormally large values with nan
df.dropna(inplace=True) #dropping all nan values 
df=df.drop_duplicates() #dropping all duplicates
df.shape

#dropping all non-numerical and repetitive features
df=df.drop_duplicates()
df=df.drop(' Destination IP', axis=1)
df=df.drop(' Source IP', axis=1)
df=df.drop('Flow ID', axis=1)
df=df.drop(' Timestamp', axis=1)
df=df.drop('Unnamed: 0', axis=1)
df=df.drop('SimillarHTTP', axis=1)
df.shape

"""**DATA PRE-PROCESSING: LABEL ENCODING**"""

print(df[' Label'].unique())

from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
df[' Label'] = le.fit_transform(df[' Label'])

print(df[' Label'].unique())

df[' Label'].value_counts() #number of each attack with new labels and dropped features

df[' Label'].hist()
plt.xlabel("Label")
plt.ylabel("Count")

from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()
scaled = scaler.fit_transform(df)

"""**OUTLIER REMOVAL USING Z-SCORE**"""

from scipy import stats
z = np.abs(stats.zscore(df))
print(z)

print(np.where(z > 10))

print(z[2][32])
print(z[2][47])
print(z[853032][39])
print(z[853879][31])

arr=np.unique(np.where(z>10)[0])
arr

len(arr)

l1=arr.tolist()

df_out = df.loc[~df.index.isin(l1)]

df_out

df.shape

df_out.shape

df_out[' Label'].value_counts() #new number of each attack with labels

"""**Splitting Test-Train Data**"""

X = df_out.iloc[:,:81]
y = df_out.iloc[:,-1]
X=X.values
X = X.reshape(X.shape[0], X.shape[1], 1)
y=y.values
from sklearn.model_selection import train_test_split 
X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=0.2,random_state=101)

X_train.shape

y_train.shape

"""**Balancing the Dataset**"""

X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1]))
print(X_train.shape)

from imblearn.over_sampling import SMOTE
smote=SMOTE('minority')
X_sm, y_sm=smote.fit_sample(X_train,y_train)
print(X_sm.shape,y_sm.shape)

X_train = np.reshape(X_train, (X_train.shape[0],X_train.shape[1],1))
print(X_train.shape)

X_sm = np.reshape(X_sm, (X_sm.shape[0],X_sm.shape[1],1))
print(X_sm.shape)

(unique, counts) = np.unique(y_sm, return_counts=True)
frequencies = np.asarray((unique, counts)).T
frequencies

"""**Hyperparameter Tuning**"""

def model_builder(hp):
  model = keras.Sequential()
  
  # Tuning the number of units in the first Convolution layer
  hp_units = hp.Int('units', min_value = 300, max_value = 400, step = 32)
  model.add(keras.layers.Conv1D(hp_units, 3, activation = 'relu', input_shape=(81,1)))
  model.add(keras.layers.Conv1D(64, 3, activation = 'relu'))
  model.add(keras.layers.MaxPooling1D())
  model.add(keras.layers.Flatten())
  model.add(keras.layers.Dense(7, activation='softmax'))

  # Tuning the learning rate for the optimizer 
  # Choosing an optimal value from 0.01, 0.001, or 0.0001
  hp_learning_rate = hp.Choice('learning_rate', values = [1e-2, 1e-3, 1e-4]) 
  
  model.compile(optimizer = keras.optimizers.Adam(learning_rate = hp_learning_rate),
                loss = keras.losses.SparseCategoricalCrossentropy(from_logits = True), 
                metrics = ['accuracy'])
  
  return model

tuner = kt.Hyperband(model_builder,
                     objective = 'val_accuracy', 
                     max_epochs = 10,
                     factor = 3,
                     directory = 'my_dir',
                     project_name = 'intro_to_kt')

class ClearTrainingOutput(tf.keras.callbacks.Callback):
  def on_train_end(*args, **kwargs):
    IPython.display.clear_output(wait = True)

tuner.search(X_sm, y_sm, epochs = 10, validation_data = (X_test, y_test), callbacks = [ClearTrainingOutput()])

# Getting the optimal hyperparameters
best_hps = tuner.get_best_hyperparameters(num_trials = 1)[0]

print(f"""
The hyperparameter search is complete. The optimal number of units in the first Convolution
layer is {best_hps.get('units')} and the optimal learning rate for the optimizer
is {best_hps.get('learning_rate')}.
""")

from tensorflow.keras.callbacks import EarlyStopping
early_stop = EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=2)

# Building the model with the optimal hyperparameters and training it on the dataset
model = tuner.hypermodel.build(best_hps)
history=model.fit(X_sm, y_sm, epochs = 10, validation_data = (X_test, y_test), callbacks = early_stop)

acc = model.evaluate(X_sm, y_sm)
print("Loss:", acc[0], " Accuracy:", acc[1])

pred = model.predict(X_test)
pred_y = pred.argmax(axis=-1)

from sklearn.metrics import confusion_matrix

cm = confusion_matrix(y_test, pred_y)
print(cm)

from sklearn import metrics
print(metrics.classification_report(y_test, pred_y, digits=3))

plt.plot(history.history['loss'], 'r')
plt.plot(history.history['val_loss'], 'b')
plt.show()

plt.plot(history.history['accuracy'], 'r')
plt.plot(history.history['val_accuracy'], 'b')
plt.show()