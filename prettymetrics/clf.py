"""
classification models
"""

import numpy as np
import pandas as pd
from tqdm import tqdm
import datetime
import time
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer, MissingIndicator
from sklearn.preprocessing import StandardScaler, OneHotEncoder, OrdinalEncoder
from sklearn.compose import ColumnTransformer
from sklearn.utils import all_estimators
from sklearn.base import ClassifierMixin
from sklearn.naive_bayes import (ComplementNB, MultinomialNB)
from sklearn.multioutput import ClassifierChain
from sklearn.ensemble import GradientBoostingClassifier
# from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.neural_network import MLPClassifier
from sklearn.cross_decomposition import CCA
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    roc_auc_score,
    f1_score,
)
import sklearn
from sklearn.utils._testing import ignore_warnings
import warnings
import xgboost

# import catboost
import lightgbm

warnings.filterwarnings("ignore")
pd.set_option("display.precision", 2)
pd.set_option("display.float_format", lambda x: "%.2f" % x)

removed_classifiers = [
    # ("CheckingClassifier", sklearn.utils._mocking.CheckingClassifier),
    ("ClassifierChain", ClassifierChain),
    ("ComplementNB", ComplementNB),
    ("GradientBoostingClassifier",GradientBoostingClassifier,),
    ("GaussianProcessClassifier",GaussianProcessClassifier,),
    # (
    #     "HistGradientBoostingClassifier",
    #     HistGradientBoostingClassifier,
    # ),
    ("MLPClassifier", MLPClassifier),
    ("LogisticRegressionCV", sklearn.linear_model.LogisticRegressionCV),
    ("MultiOutputClassifier", sklearn.multioutput.MultiOutputClassifier),
    ("MultinomialNB", MultinomialNB),
    ("OneVsOneClassifier", sklearn.multiclass.OneVsOneClassifier),
    ("OneVsRestClassifier", sklearn.multiclass.OneVsRestClassifier),
    ("OutputCodeClassifier", sklearn.multiclass.OutputCodeClassifier),
    (
        "RadiusNeighborsClassifier",
        sklearn.neighbors.RadiusNeighborsClassifier,
    ),
    ("VotingClassifier", sklearn.ensemble.VotingClassifier),
]


CLASSIFIERS = [est for est in all_estimators() if
               (issubclass(est[1], ClassifierMixin) and (est[0] not in removed_classifiers))]

CLASSIFIERS.append(("XGBClassifier", xgboost.XGBClassifier))
CLASSIFIERS.append(("LGBMClassifier", lightgbm.LGBMClassifier))
# CLASSIFIERS.append(('CatBoostClassifier',catboost.CatBoostClassifier))
CLASSIFIERS_DICT = {key : value for key, value in CLASSIFIERS}

numeric_transformer = Pipeline(
    steps=[("imputer", SimpleImputer(strategy="mean")), ("scaler", StandardScaler())]
)

categorical_transformer_low = Pipeline(
    steps=[
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
        ("encoding", OneHotEncoder(handle_unknown="ignore", sparse=False)),
    ]
)

categorical_transformer_high = Pipeline(
    steps=[
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
        # 'OrdianlEncoder' Raise a ValueError when encounters an unknown value. Check https://github.com/scikit-learn/scikit-learn/pull/13423
        ("encoding", OrdinalEncoder()),
    ]
)

# Helper function


def get_card_split(df, cols, n=11):
    """
    Splits categorical columns into 2 lists based on cardinality (i.e # of unique values)
    Parameters
    ----------
    df : Pandas DataFrame
        DataFrame from which the cardinality of the columns is calculated.
    cols : list-like
        Categorical columns to list
    n : int, optional (default=11)
        The value of 'n' will be used to split columns.
    Returns
    -------
    card_low : list-like
        Columns with cardinality < n
    card_high : list-like
        Columns with cardinality >= n
    """
    cond        = df[cols].nunique() > n
    card_high   = cols[cond]
    card_low    = cols[~cond]

    return card_low, card_high



class Classifier:
    """
    This module helps in fitting to all the classification algorithms that are available in Scikit-learn
    Parameters
    ----------
    verbose : int, optional (default=0)
        For the liblinear and lbfgs solvers set verbose to any positive
        number for verbosity.
    ignore_warnings : bool, optional (default=True)
        When set to True, the warning related to algorigms that are not able to run are ignored.
    custom_metric : function, optional (default=None)
        When function is provided, models are evaluated based on the custom evaluation metric provided.
    prediction : bool, optional (default=False)
        When set to True, the predictions of all the models models are returned as dataframe.
    classifiers : list, optional (default="all")
        When function is provided, trains the chosen classifier(s).

    Examples
    --------
    >>> from prettymetrics.clf import Classifier
    >>> from sklearn.datasets import load_breast_cancer
    >>> from sklearn.model_selection import train_test_split
    >>> data = load_breast_cancer()
    >>> X = data.data
    >>> y= data.target
    >>> X_train, X_test, y_train, y_test = train_test_split(X, y,test_size=.5,random_state =123)
    >>> clf = Classifier(verbose=0,ignore_warnings=True, custom_metric=None)
    >>> models,predictions = clf.fit(X_train, X_test, y_train, y_test)
    >>> model_dictionary = clf.provide_models(X_train,X_test,y_train,y_test)
    >>> models
    | Model                          |   Accuracy |   Balanced Accuracy |   ROC AUC |   F1 Score |   Time Taken |
    |:-------------------------------|-----------:|--------------------:|----------:|-----------:|-------------:|
    | LinearSVC                      |   0.989474 |            0.987544 |  0.987544 |   0.989462 |    0.0150008 |
    | SGDClassifier                  |   0.989474 |            0.987544 |  0.987544 |   0.989462 |    0.0109992 |
    | MLPClassifier                  |   0.985965 |            0.986904 |  0.986904 |   0.985994 |    0.426     |
    | Perceptron                     |   0.985965 |            0.984797 |  0.984797 |   0.985965 |    0.0120046 |
    | LogisticRegression             |   0.985965 |            0.98269  |  0.98269  |   0.985934 |    0.0200036 |
    | LogisticRegressionCV           |   0.985965 |            0.98269  |  0.98269  |   0.985934 |    0.262997  |
    | SVC                            |   0.982456 |            0.979942 |  0.979942 |   0.982437 |    0.0140011 |
    | CalibratedClassifierCV         |   0.982456 |            0.975728 |  0.975728 |   0.982357 |    0.0350015 |
    | PassiveAggressiveClassifier    |   0.975439 |            0.974448 |  0.974448 |   0.975464 |    0.0130005 |
    | LabelPropagation               |   0.975439 |            0.974448 |  0.974448 |   0.975464 |    0.0429988 |
    | LabelSpreading                 |   0.975439 |            0.974448 |  0.974448 |   0.975464 |    0.0310006 |
    | RandomForestClassifier         |   0.97193  |            0.969594 |  0.969594 |   0.97193  |    0.033     |
    | GradientBoostingClassifier     |   0.97193  |            0.967486 |  0.967486 |   0.971869 |    0.166998  |
    | QuadraticDiscriminantAnalysis  |   0.964912 |            0.966206 |  0.966206 |   0.965052 |    0.0119994 |
    | HistGradientBoostingClassifier |   0.968421 |            0.964739 |  0.964739 |   0.968387 |    0.682003  |
    | RidgeClassifierCV              |   0.97193  |            0.963272 |  0.963272 |   0.971736 |    0.0130029 |
    | RidgeClassifier                |   0.968421 |            0.960525 |  0.960525 |   0.968242 |    0.0119977 |
    | AdaBoostClassifier             |   0.961404 |            0.959245 |  0.959245 |   0.961444 |    0.204998  |
    | ExtraTreesClassifier           |   0.961404 |            0.957138 |  0.957138 |   0.961362 |    0.0270066 |
    | KNeighborsClassifier           |   0.961404 |            0.95503  |  0.95503  |   0.961276 |    0.0560005 |
    | BaggingClassifier              |   0.947368 |            0.954577 |  0.954577 |   0.947882 |    0.0559971 |
    | BernoulliNB                    |   0.950877 |            0.951003 |  0.951003 |   0.951072 |    0.0169988 |
    | LinearDiscriminantAnalysis     |   0.961404 |            0.950816 |  0.950816 |   0.961089 |    0.0199995 |
    | GaussianNB                     |   0.954386 |            0.949536 |  0.949536 |   0.954337 |    0.0139935 |
    | NuSVC                          |   0.954386 |            0.943215 |  0.943215 |   0.954014 |    0.019989  |
    | DecisionTreeClassifier         |   0.936842 |            0.933693 |  0.933693 |   0.936971 |    0.0170023 |
    | NearestCentroid                |   0.947368 |            0.933506 |  0.933506 |   0.946801 |    0.0160074 |
    | ExtraTreeClassifier            |   0.922807 |            0.912168 |  0.912168 |   0.922462 |    0.0109999 |
    | CheckingClassifier             |   0.361404 |            0.5      |  0.5      |   0.191879 |    0.0170043 |
    | DummyClassifier                |   0.512281 |            0.489598 |  0.489598 |   0.518924 |    0.0119965 |
    """

    def __init__(
        self,
        verbose         = 0,
        ignore_warnings = True,
        custom_metric   = None,
        predictions     = False,
        random_state    = 42,
        classifiers     = "all"
    ):
        self.verbose            = verbose
        self.ignore_warnings    = ignore_warnings
        self.custom_metric      = custom_metric
        self.predictions        = predictions
        self.models             = {}
        self.random_state       = random_state
        self.classifiers        = classifiers

    def get_classifiers(self):

        if self.classifiers == "all":
            self.classifiers = CLASSIFIERS
            return
        
        try:
            temp_list = [(classifier, CLASSIFIERS_DICT[classifier]) for classifier in self.classifiers]
            self.classifiers = temp_list
        except Exception as exception:
            print(exception)
            print("Invalid Classifier(s)")

    def fit(self, X_train, X_test, y_train, y_test):
        """Fit Classification algorithms to X_train and y_train, predict and score on X_test, y_test.
        Parameters
        ----------
        X_train : array-like,
            Training vectors, where rows is the number of samples
            and columns is the number of features.
        X_test : array-like,
            Testing vectors, where rows is the number of samples
            and columns is the number of features.
        y_train : array-like,
            Training vectors, where rows is the number of samples
            and columns is the number of features.
        y_test : array-like,
            Testing vectors, where rows is the number of samples
            and columns is the number of features.
        Returns
        -------
        scores : Pandas DataFrame
            Returns metrics of all the models in a Pandas DataFrame.
        predictions : Pandas DataFrame
            Returns predictions of all the models in a Pandas DataFrame.
        """
        accuracy_list           = []
        balanced_accuracy_list  = []
        roc_auc_list            = []
        f1_list                 = []
        names                   = []
        time_list               = []
        predictions             = {}

        if self.custom_metric:
            CUSTOM_METRIC = []

        if isinstance(X_train, np.ndarray):
            X_train = pd.DataFrame(X_train)
            X_test  = pd.DataFrame(X_test)

        numeric_features        = X_train.select_dtypes(include=[np.number]).columns
        categorical_features    = X_train.select_dtypes(include=["object"]).columns

        categorical_low, categorical_high = get_card_split(
            X_train, categorical_features
        )

        preprocessor = ColumnTransformer(
            transformers = [
                ("numeric", numeric_transformer, numeric_features),
                ("categorical_low", categorical_transformer_low, categorical_low),
                ("categorical_high", categorical_transformer_high, categorical_high),
            ]
        )

        self.get_classifiers()

        for name, model in tqdm(self.classifiers):
            start = time.time()
            try:
                if "random_state" in model().get_params().keys():
                    pipe = Pipeline(
                        steps = [
                            ("preprocessor", preprocessor),
                            ("classifier", model(random_state=self.random_state)),
                        ]
                    )
                else:
                    pipe = Pipeline(
                        steps = [("preprocessor", preprocessor), ("classifier", model())]
                    )

                pipe.fit(X_train, y_train)

                self.models[name]   = pipe
                y_pred              = pipe.predict(X_test)
                accuracy            = accuracy_score(y_test, y_pred, normalize=True)
                b_accuracy          = balanced_accuracy_score(y_test, y_pred)
                f1                  = f1_score(y_test, y_pred, average="weighted")
                
                try:
                    roc_auc = roc_auc_score(y_test, y_pred)
                except Exception as exception:
                    roc_auc = None
                    if not self.ignore_warnings:
                        print("ROC AUC couldn't be calculated for " + name)
                        print(exception)

                # indexes.append()
                names.append(name)
                accuracy_list.append(accuracy)
                balanced_accuracy_list.append(b_accuracy)
                roc_auc_list.append(roc_auc)
                f1_list.append(f1)
                time_list.append(time.time() - start)

                if self.custom_metric:
                    custom_metric = self.custom_metric(y_test, y_pred)
                    CUSTOM_METRIC.append(custom_metric)

                if self.verbose > 0:
                    current_metric = {
                        "Model"                     : name,
                        "Accuracy"                  : accuracy,
                        "Balanced Accuracy"         : b_accuracy,
                        "ROC AUC"                   : roc_auc,
                        "F1 Score"                  : f1,
                        "Time taken"                : time.time() - start,
                    }

                    if self.custom_metric:
                        current_metric[self.custom_metric.__name__] = custom_metric
                    
                    print(current_metric)

                if self.predictions:
                    predictions[name] = y_pred

            except Exception as exception:
                if not self.ignore_warnings:
                    print(name + " model failed to execute")
                    print(exception)

        # indexes = scores.index[lambda x: x in scores.indexes()]

        scores = pd.DataFrame(
            {
                "Model"             : names,
                "Accuracy"          : accuracy_list,
                "Balanced Accuracy" : balanced_accuracy_list,
                "ROC AUC"           : roc_auc_list,
                "F1 Score"          : f1_list,
                "Time Taken"        : time_list,
            }
        )

        if self.custom_metric:
            scores[self.custom_metric.__name__] = CUSTOM_METRIC

        # Sort the final metris by Balance Accuracy
        scores = scores.sort_values(
            by              = "Balanced Accuracy", 
            ascending       = False,
            # ignore_index    = True # This is not helping on the indexing
        ).set_index(
            "Model"
        )

        # TODO: We need to index the score so we can see how many algorithms used
        indexes = scores.index.tolist()
        # scores['L_Index'] = indexes

        if self.predictions:
            predictions_df = pd.DataFrame.from_dict(predictions)

        return scores, predictions_df if self.predictions is True else scores

    def provide_models(self, X_train, X_test, y_train, y_test):
        """
        This function returns all the model objects trained in fit function.
        If fit is not called already, then we call fit and then return the models.
        Parameters
        ----------
        X_train : array-like,
            Training vectors, where rows is the number of samples
            and columns is the number of features.
        X_test : array-like,
            Testing vectors, where rows is the number of samples
            and columns is the number of features.
        y_train : array-like,
            Training vectors, where rows is the number of samples
            and columns is the number of features.
        y_test : array-like,
            Testing vectors, where rows is the number of samples
            and columns is the number of features.
        Returns
        -------
        models: dict-object,
            Returns a dictionary with each model pipeline as value 
            with key as name of models.
        """
        if len(self.models.keys()) == 0:
            self.fit(X_train, X_test, y_train,y_test)

        return self.models