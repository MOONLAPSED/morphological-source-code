from tempfile import NamedTemporaryFile, TemporaryDirectory
import math

def sigmoid(x):
    """ Sigmoid activation function for input x """
    return 1 / (1 + math.exp(-x))

def dot_product(input_data, weights):
    """ Computes the dot product of input_data and weights """
    return sum(i * w for i, w in zip(input_data, weights))

def forward_propagation(input_data, weights, bias):
    """
    Computes the forward propagation of the perceptron and returns the result
    after applying the sigmoid activation function.
    :param input_data: input data
    :param weights: weights
    :param bias: bias
    :return: activated output
    """
    # Compute the dot product and add bias
    return sigmoid(dot_product(input_data, weights) + bias)

def calculate_error(Y, Y_predicted):
    """
    Computes the binary cross-entropy error
    :param Y: label
    :param Y_predicted: predicted result
    :return: binary cross-entropy error
    """
    if Y_predicted == 1:
        return -Y * math.log(Y_predicted)
    else:
        return -Y * math.log(Y_predicted) - (1 - Y) * math.log(1 - Y_predicted)

def gradient(target, actual, X):
    """
    Computes the gradient of weights and bias
    :param target: label
    :param actual: prediction
    :param X: input
    :return: weight gradient, bias gradient
    """
    dW = [-(target - actual) * x for x in X]
    db = target - actual
    return dW, db

def update_parameters(W, b, dW, db, learning_rate):
    """
    Updates the weights and bias values
    :param W: weights
    :param dW: weight gradient
    :param db: bias gradient
    :param learning_rate: learning rate
    :return: new weights, new bias
    """
    W = [w - dw * learning_rate for w, dw in zip(W, dW)]
    b = b - db * learning_rate
    return W, b

def train(X, Y, weights, bias, epochs, learning_rate):
    """
    Trains the perceptron using stochastic updates
    :param X: array of input data
    :param Y: output labels
    :param weights: array of weights
    :param bias: bias
    :param epochs: number of epochs
    :param learning_rate: learning rate
    :return: new weights, new bias
    """
    for i in range(epochs):
        sum_error = 0.0
        for j in range(len(X)):
            Y_predicted = forward_propagation(X[j], weights, bias)  # predicted label
            sum_error += calculate_error(Y[j], Y_predicted)  # compute error
            dW, db = gradient(Y[j], Y_predicted, X[j])  # find gradient
            weights, bias = update_parameters(weights, bias, dW, db, learning_rate)  # update parameters
        print("epochs: ", i, "error: ", sum_error)
    return weights, bias

# Initialize parameters
# Two data points
X = [
    [2.78, 2.55],
    [1.46, 2.36],
    [3.39, 4.40],
    [1.38, 1.85],
    [3.06, 3.00],
    [7.62, 2.75],
    [5.33, 2.08],
    [6.92, 1.77],
    [8.67, -0.24],
    [7.67, 3.50]
]

Y = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]  # actual labels
weights = [0.0, 0.0]  # perceptron weights
bias = 0.0  # bias
learning_rate = 0.1  # learning rate
epochs = 10  # epochs

print("Before training")
print("weights:", weights, "bias:", bias)

weights, bias = train(X, Y, weights, bias, epochs, learning_rate)  # train the function

print("\nAfter training")
print("weights:", weights, "bias:", bias)

# Predict values
predicted_labels = [forward_propagation(x, weights, bias) for x in X]
print("Target labels:  ", Y)
print(" Predicted labels:", [1 if label > 0.5 else 0 for label in predicted_labels])