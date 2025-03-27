# from langchain_huggingface import HuggingFaceEmbeddings

# def get_embedding_function():
#     # model_name = "sentence-transformers/all-MiniLM-L6-v2" # Primeiro que usei
#     # model_name = "sentence-transformers/all-MiniLM-L12-v2" # Segundo que usei e aprovei
#     # model_name = "BAAI/bge-small-en-v1.5"

#     model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

#     return HuggingFaceEmbeddings(model_name=model_name)


# from langchain_huggingface import HuggingFaceEmbeddings

# def get_embedding_function():
#     return HuggingFaceEmbeddings(
#         model_name="BAAI/bge-small-en-v1.5",
#         model_kwargs={"trust_remote_code": True}
#     )

from langchain_huggingface import HuggingFaceEmbeddings

def get_embedding_function():
    return HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-small",
        model_kwargs={"trust_remote_code": True}
    )
