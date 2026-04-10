from llm.pipeline import run_pipeline

if __name__ == "__main__":
    while True:
        query = input(">> ")
        result = run_pipeline(query)
        print(result)