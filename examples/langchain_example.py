"""
LangChain integration example.
Requires: pip install silentefail[langchain] and OPENAI_API_KEY set.
"""
from pydantic import BaseModel
from silentefail import Auditor, FailureClass
from silentefail.runners import LangChainRunner


class ExtractedData(BaseModel):
    name: str
    value: float
    category: str


class InputData(BaseModel):
    text: str
    context: str


def build_chain():
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    llm = ChatOpenAI(model="gpt-4o-mini")
    parser = JsonOutputParser(pydantic_object=ExtractedData)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract structured data from the text. Return JSON matching: name (str), value (float), category (str)."),
        ("human", "Text: {text}\nContext: {context}"),
    ])

    return prompt | llm | parser


if __name__ == "__main__":
    chain = build_chain()
    runner = LangChainRunner(chain)

    auditor = Auditor(
        pipeline=runner,
        input_schema=InputData,
        output_schema=ExtractedData,
        golden_dataset=[
            ("What is 2+2?", "4", ["4", "four"]),
            ("Capital of France?", "Paris", ["Paris"]),
        ],
        context_window=128000,
        test_inputs=[
            {"text": "Revenue was $1.2M", "context": "Q3 report"},
            {"text": "Growth rate: 45%", "context": "Annual summary"},
        ],
    )

    report = auditor.run()
    report.summary()
    report.export("langchain_report.html")
