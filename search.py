from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class DSSearch:

    def __init__(self, dataset):
        self.questions = [item["question"] for item in dataset]
        self.answers = [item["answer"] for item in dataset]

        self.vectorizer = TfidfVectorizer()
        self.question_vectors = self.vectorizer.fit_transform(self.questions)

    def get_answer(self, query):

        query_vec = self.vectorizer.transform([query])
        similarity = cosine_similarity(query_vec, self.question_vectors)

        index = similarity.argmax()

        return self.answers[index]