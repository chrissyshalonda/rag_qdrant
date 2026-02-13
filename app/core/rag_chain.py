from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.prompts import ChatPromptTemplate
from app.database import get_vector_store
from config.config import Settings


def create_rag_chain(settings: Settings):
    llm = HuggingFaceEndpoint(
        repo_id="meta-llama/Llama-3.1-8B-Instruct",
        huggingfacehub_api_token=settings.huggingfacehub_api_token,
        task="text-generation",
        temperature=0.1,
    )
    chat_model = ChatHuggingFace(llm=llm)

    vector_store = get_vector_store(settings)
    retriever = vector_store.as_retriever(
        search_kwargs={"k": settings.retriever_k}
    )

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """Ты профессиональный ассистент. Твоя задача — отвечать на вопросы, используя ТОЛЬКО предоставленный контекст.
        Если в контексте нет ответа, так и скажи: "Я не нашел информации в ваших документах".
        
        При ответе обязательно указывай источник (название файла и страницу), если они есть в контексте.
        
        Контекст:
        {context}"""),
        ("human", "{question}"),
    ])

    def answer_question(question: str) -> str:
        docs = retriever.invoke(question)
        
        enriched_context = ""
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "Неизвестный источник")
            page = doc.metadata.get("page", "?")
            enriched_context += f"\n--- Отрывок {i+1} (Источник: {source}, Стр: {page}) ---\n{doc.page_content}\n"

        formatted_prompt = prompt_template.format_messages(
            question=question, 
            context=enriched_context
        )

        response = chat_model.invoke(formatted_prompt)
        return response.content

    return answer_question