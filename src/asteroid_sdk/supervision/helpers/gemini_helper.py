import copy
import json
from typing import List

from google.ai.generativelanguage_v1beta import Content, Part, Candidate
from google.ai.generativelanguage_v1beta import FunctionCall, Candidate as TypeImport, \
    GenerateContentResponse as BetaContent
from google.generativeai import GenerativeModel
from google.generativeai.types import GenerateContentResponse
from google.protobuf.json_format import MessageToDict

from asteroid_sdk.supervision.helpers.model_provider_helper import Provider
from asteroid_sdk.supervision.model.tool_call import ToolCall


class GeminiHelper:
    def get_tool_call_from_response(self, response: GenerateContentResponse) -> List[ToolCall]:
        tools = []
        for part in response.parts:
            if fc := part.function_call:
                # Surely theres a way to clear up these args
                params = {arg: value for arg, value in fc.args.items()}
                call = ToolCall(
                    message_id=None,
                    tool_name=fc.name,
                    tool_params=params,
                    language_model_tool_call=fc,
                    message=copy.deepcopy(response)
                )
                tools.append(call)
        return tools

    def generate_fake_tool_call(self, response: GenerateContentResponse) -> ToolCall:
        raise ValueError("Not implemented yet")

    # TODO - implement this properly, we aren't using chat supervisors yet for Gemini, so no point doing this + code
    #  doesn't work properly!
    def generate_message_from_fake_tool_call(self, response: GenerateContentResponse) -> GenerateContentResponse:
        return response
        # if fc := response.parts[0].function_call:
        #     if fc.name == MESSAGE_TOOL_NAME:
        #         response.parts[0].content = fc.args["message"]
        #         response.parts[0].function_call = None
        # return response

    def upsert_tool_call(self, response: GenerateContentResponse, tool_call: FunctionCall) -> GenerateContentResponse:
        """
        This method assumes that we only have one tool call in the response.choices[0].message.tool_calls. No protection
        is added, so if there is more than 1 there, it'll overwrite them all

        :param response: ChatCompletion
        :param tool_call: ChatCompletionMessageToolCall
        :return: ChatCompletion
        """
        for part in response.parts:
            if fc := part.function_call:
                if fc.name == tool_call.name:
                    part.function_call = tool_call

        return response

    def generate_new_response_with_rejection_message(self, rejection_message: str) -> GenerateContentResponse:
        part = Part(text=rejection_message)
        content = Content(parts=[part], role="model")
        candidate = Candidate(
            content=content,
            index=0,
            # This has to be this import as the 'chat' bit is checking this enum, so has to be from `protos`
            finish_reason=TypeImport.FinishReason.STOP,
            safety_ratings=[],
            citation_metadata=None,
            token_count=0,
            avg_logprobs=0.0,
            logprobs_result=None
        )

        beta_response = BetaContent(candidates=[candidate])
        # Can't generate the model directly, need to go via this, and then instantiate with `from_response
        return GenerateContentResponse.from_response(beta_response)


    def get_provider(self) -> Provider:
        return Provider.GEMINI

    def convert_model_kwargs_to_json(self, request_kwargs: dict) -> str:
        kwargs_to_convert = copy.deepcopy(request_kwargs)
        contents = kwargs_to_convert.get('contents')
        for i, part in enumerate(contents):
            if isinstance(part, dict):
                continue
            content_part_dict = MessageToDict(part._pb)
            kwargs_to_convert['contents'][i] = content_part_dict

        tools_list = []
        if tools := kwargs_to_convert.get('tools', False):
            proto_list = tools.to_proto()
            for i, tool in enumerate(proto_list):
                tool_dict = MessageToDict(tool._pb)
                tools_list.append(tool_dict)
        kwargs_to_convert['tools'] = tools_list

        return json.dumps(kwargs_to_convert)

    # TODO - maybe change the args here to stop us passing in the client
    def resample_response(self, feedback_message, args, request_kwargs, completions: GenerativeModel):
        copied_kwargs = copy.deepcopy(request_kwargs)
        current_contents = copied_kwargs["contents"]
        current_contents.append({"role": "user", 'parts': [{"text": feedback_message}]})
        copied_kwargs["contents"] = current_contents

        result = completions.generate_content(**copied_kwargs)

        return result, copied_kwargs
