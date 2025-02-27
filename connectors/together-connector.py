import os
from typing import Any

from moonshot.src.connectors.connector import Connector, perform_retry
from moonshot.src.connectors.connector_response import ConnectorResponse
from moonshot.src.connectors_endpoints.connector_endpoint_arguments import (
    ConnectorEndpointArguments,
)
from together import AsyncTogether


class TogetherConnector(Connector):
    def __init__(self, ep_arguments: ConnectorEndpointArguments):
        # Initialize super class
        super().__init__(ep_arguments)

        # Initialize the AsyncTogether client with the API key. The API key is selected from the token
        # attribute if available; otherwise, it defaults to the TOGETHER_API_KEY environment variable.
        api_key = self.token or os.getenv("TOGETHER_API_KEY") or ""
        self._client = AsyncTogether(api_key=api_key)

    @Connector.rate_limited
    @perform_retry
    async def get_response(self, prompt: str) -> ConnectorResponse:
        """
        Asynchronously sends a prompt to the Together API and returns the generated response.

        This method constructs a request with the given prompt, optionally prepended and appended with
        predefined strings, and sends it to the Together API. If a system prompt is set, it is included in the
        request. The method then awaits the response from the API, processes it, and returns the resulting message
        content wrapped in a ConnectorResponse object.

        Args:
            prompt (str): The input prompt to send to the Together API.

        Returns:
            ConnectorResponse: An object containing the text response generated by the Together model.
        """
        connector_prompt = f"{self.pre_prompt}{prompt}{self.post_prompt}"
        if self.system_prompt:
            together_request = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": connector_prompt},
            ]
        else:
            together_request = [{"role": "user", "content": connector_prompt}]

        # Merge self.optional_params with additional parameters
        new_params = {
            **self.optional_params,
            "model": self.model,
            "messages": together_request,
        }
        response = await self._client.chat.completions.create(**new_params)
        return ConnectorResponse(response=await self._process_response(response))

    async def _process_response(self, response: Any) -> str:
        """
        Process the response from Together's API and return the message content.

        This method processes the response received from Together's API call, specifically targeting
        the chat completion response structure. It extracts the message content from the first choice
        provided in the response, which is expected to contain the relevant information or answer.

        Args:
            response (Any): The response object received from a Together API call. It is expected to
            follow the structure of Together's chat completion response.

        Returns:
            str: A string containing the message content from the first choice in the response. This
            content represents the AI-generated text based on the input prompt.
        """
        return response.choices[0].message.content
