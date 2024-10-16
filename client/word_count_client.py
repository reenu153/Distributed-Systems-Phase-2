import argparse
import asyncio
import websockets
import matplotlib
matplotlib.use('Agg')
import time
import matplotlib.pyplot as plt
import numpy as np

async def send_word_count_request(fileName, keyword):
    uri = "ws://load_balancer:8765"
    async with websockets.connect(uri) as websocket:
        request = f"{fileName},{keyword}"
        await websocket.send(request)
        response = await websocket.recv()
        result, server_info = response.split("|")
        
        if "Text file" in result:
            return result, server_info  # Return the error message
        return int(result), server_info  # Otherwise, return the count as an integer

async def serve_warmup(filename, keyword):
    """
    Perform a warm-up request using the first keyword-filename pair.
    """
    print(f"Performing warm-up request with {filename}, {keyword}...")
    await send_word_count_request(filename, keyword)  # Ignore the result, it's just a warm-up
    print("Warm-up request completed.\n")

def plot_metrics(latencies):
    x_labels = [pair[0] for pair in latencies]
    normal_latencies = [pair[1] for pair in latencies]
    cache_latencies = [pair[2] for pair in latencies]
    
    x = np.arange(len(x_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars1 = ax.bar(x - width/2, normal_latencies, width, label='Normal Latency')
    bars2 = ax.bar(x + width/2, cache_latencies, width, label='Cache Latency')

    ax.set_xlabel("Keyword-Filename Pair")
    ax.set_ylabel("Latency (milliseconds)")
    ax.set_title("Normal Latency vs Cache Latency (ms) for Keyword-Filename Pairs")
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=45)
    ax.legend()

    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig("/output/latency_plot.png")
    print("Plot saved as /output/latency_plot.png")

def plot_count(counts):
    x_labels = [pair[0] for pair in counts]
    count_values = [pair[1] for pair in counts]
    
    x = np.arange(len(x_labels))

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.bar(x, count_values, width=0.5, color='green')

    ax.set_xlabel("Keyword-Filename Pair")
    ax.set_ylabel("Word Count")
    ax.set_title("Word Count for Each Keyword-Filename Pair")
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=45)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig("/output/count.png")
    print("Plot saved as /output/count.png")

async def handle_batch_requests():
    while True:  # Infinite loop to continuously accept batch requests
        num_pairs = int(input("Enter the number of keyword-filename pairs: "))
        keyword_filename_pairs = []

        for _ in range(num_pairs):
            keyword = input("Enter the keyword: ")
            filename = input("Enter the filename: ")
            keyword_filename_pairs.append((filename, keyword))

        # Use the first keyword-filename pair for the warm-up
        first_filename, first_keyword = keyword_filename_pairs[0]
        await serve_warmup(first_filename, first_keyword)  # Perform the warm-up

        latencies = []
        counts = []
        
        for filename, keyword in keyword_filename_pairs:
            start_time = time.time()
            word_count, server_info = await send_word_count_request(filename, keyword)
            
            if isinstance(word_count, str):  # If the result is an error message, print it and continue
                print(f"Error from {server_info}: {word_count}")
                continue

            latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            print(f"First request handled by {server_info}: Latency = {latency:.4f} ms, Word Count = {word_count}")
            
            start_time_cache = time.time()
            cache_word_count, server_info_cache = await send_word_count_request(filename, keyword)
            
            if isinstance(cache_word_count, str):  # Handle cache errors
                print(f"Error from {server_info_cache}: {cache_word_count}")
                continue
            
            cache_latency = (time.time() - start_time_cache) * 1000
            print(f"Cache hit handled by {server_info_cache}: Cache Latency = {cache_latency:.4f} ms")

            latencies.append((f"{keyword}-{filename}", latency, cache_latency))
            counts.append((f"{keyword}-{filename}", word_count))

        plot_metrics(latencies)
        plot_count(counts)

if __name__ == "__main__":
    try:
        asyncio.run(handle_batch_requests())
    except KeyboardInterrupt:
        print("\nBye!")