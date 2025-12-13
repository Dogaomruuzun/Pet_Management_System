
from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline


def clamp(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return np.minimum(np.maximum(x, lo), hi)


def train_lifespan(rng: np.random.Generator) -> LinearRegression:
    # Feature: age (years), Target: expected lifespan (years)
    age = rng.uniform(0, 20, size=600).reshape(-1, 1)
    lifespan = 16 - 0.6 * age[:, 0] + rng.normal(0, 0.8, size=age.shape[0])
    lifespan = clamp(lifespan, 2, 20)
    m = LinearRegression()
    m.fit(age, lifespan)
    return m


def train_health_score(rng: np.random.Generator) -> LinearRegression:
    # Features: age, weight, Target: 0-100 score (synthetic)
    age = rng.uniform(0, 20, size=1200)
    weight = rng.uniform(0.5, 50.0, size=1200)

    age_penalty = (age - 6) ** 2 / 3.5
    # "ideal" weight depends weakly on age
    ideal_w = 4 + 0.9 * age
    w_penalty = ((weight - ideal_w) ** 2) / 12.0
    score = 95 - 9 * age_penalty - 6 * w_penalty + rng.normal(0, 3.5, size=age.shape[0])
    score = clamp(score, 0, 100)

    X = np.vstack([age, weight]).T
    m = LinearRegression()
    m.fit(X, score)
    return m


def train_breed_risk(rng: np.random.Generator) -> Pipeline:
    # Feature: age, Label: Low/Medium/High (synthetic)
    age = rng.uniform(0, 20, size=800).reshape(-1, 1)
    # Simple rule with noise
    risk_score = age[:, 0] + rng.normal(0, 2.0, size=age.shape[0])
    y = np.where(risk_score < 6, "Low", np.where(risk_score < 12, "Medium", "High"))

    # Use logistic regression on age
    clf = LogisticRegression(max_iter=2000)
    clf.fit(age, y)
    return clf


@dataclass
class Condition:
    label: str
    templates: List[str]


def build_symptom_dataset(rng: np.random.Generator, n_per_label: int = 120) -> Tuple[List[str], List[str]]:
    conditions = [
        Condition(
            "Gastroenteritis",
            [
                "{sp} has vomiting and diarrhea",
                "vomiting, diarrhea, no appetite",
                "watery stool, vomiting, tired",
                "throwing up after eating, diarrhea",
                "dehydration, diarrhea, vomiting",
            ],
        ),
        Condition(
            "Upper Respiratory Infection",
            [
                "coughing and sneezing",
                "runny nose, sneezing, watery eyes",
                "{sp} is coughing, low energy",
                "wheezing, cough, mild fever",
                "sneezing, congestion, reduced appetite",
            ],
        ),
        Condition(
            "Ear Infection",
            [
                "scratching ears, head shaking",
                "ear odor, ear redness, itching",
                "{sp} keeps shaking head and scratching ear",
                "brown discharge from ear, discomfort",
                "sensitive ear, pain when touched",
            ],
        ),
        Condition(
            "Fleas / Skin Irritation",
            [
                "itchy skin, constant scratching",
                "flea dirt, biting skin, hair loss",
                "red bumps, scratching, restless",
                "skin irritation and licking paws",
                "scratching at night, tiny bugs seen",
            ],
        ),
        Condition(
            "Arthritis / Joint Pain",
            [
                "limping, stiffness, difficulty jumping",
                "joint pain, slow movement, stiff legs",
                "{sp} has trouble standing up, limping",
                "reluctant to climb stairs, stiffness",
                "reduced activity, sore joints",
            ],
        ),
        Condition(
            "Diabetes Warning",
            [
                "drinking more water, frequent urination",
                "weight loss, thirsty, peeing a lot",
                "{sp} is very thirsty and losing weight",
                "increased hunger, frequent urination",
                "lethargy, excessive thirst, sweet breath",
            ],
        ),
    ]

    extra_words = ["today", "since yesterday", "for 2 days", "mild", "severe", "on and off", "after meal", "at night"]
    species_words = ["Dog", "Cat", "Pet"]

    texts, labels = [], []
    for cond in conditions:
        for _ in range(n_per_label):
            sp = rng.choice(species_words)
            t = rng.choice(cond.templates).format(sp=sp)
            # add a couple random modifiers
            mods = rng.choice(extra_words, size=rng.integers(0, 3), replace=False)
            sentence = (t + " " + " ".join(mods)).strip()
            texts.append(sentence)
            labels.append(cond.label)

    # Shuffle
    idx = np.arange(len(texts))
    rng.shuffle(idx)
    texts = [texts[i] for i in idx]
    labels = [labels[i] for i in idx]
    return texts, labels


def train_symptom_classifier(rng: np.random.Generator):
    texts, labels = build_symptom_dataset(rng, n_per_label=140)

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        max_features=5000,
    )
    X = vectorizer.fit_transform(texts)

    clf = LogisticRegression(max_iter=4000)
    clf.fit(X, labels)
    return vectorizer, clf


def main() -> None:
    rng = np.random.default_rng(42)

    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
    os.makedirs(model_dir, exist_ok=True)

    lifespan_model = train_lifespan(rng)
    health_model = train_health_score(rng)
    breed_model = train_breed_risk(rng)
    diag_vectorizer, diag_model = train_symptom_classifier(rng)

    with open(os.path.join(model_dir, "lifespan_model.pkl"), "wb") as f:
        pickle.dump(lifespan_model, f)

    with open(os.path.join(model_dir, "health_model.pkl"), "wb") as f:
        pickle.dump(health_model, f)

    with open(os.path.join(model_dir, "breed_model.pkl"), "wb") as f:
        pickle.dump(breed_model, f)

    with open(os.path.join(model_dir, "diagnose_vectorizer.pkl"), "wb") as f:
        pickle.dump(diag_vectorizer, f)

    with open(os.path.join(model_dir, "diagnose_model.pkl"), "wb") as f:
        pickle.dump(diag_model, f)

    print("Saved models to:", model_dir)


if __name__ == "__main__":
    main()
