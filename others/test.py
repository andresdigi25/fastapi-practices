import sys
import httpx
import asyncio
import time
import itertools

async def send_request(client, url):
    try:
        response = await client.get(url)
        return response.status_code, response.text
    except Exception as e:
        print(f'Request error ocurred: {e}')
    return None, None

async def send_concurrent_requests(url, num_requests):
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=200) 
    async with httpx.AsyncClient(limits=limits, timeout=None) as client:
        responses = await asyncio.gather(
            *[send_request(client, url) for _ in range(num_requests)])
    return responses

if __name__ == '__main__':
    endpoint, num_requests = sys.argv[1], int(sys.argv[2])
    start = time.time()
    responses = asyncio.run(
        send_concurrent_requests(
            f'http://localhost:8000/{endpoint}',
              num_requests
        )
    )
    end_time = time.time()
    print(f'Completed {num_requests} requests in {end_time - start} seconds')
    sucessful_requests = [response for response in responses if response[0] == 200]
    print(f'Sucessful Responses: {len(sucessful_requests)}, Failed Responses: {num_requests - len(sucessful_requests)}')
    

