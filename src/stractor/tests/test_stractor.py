import pytest

from stractor.core import Stractor
from stractor.model import Function, SourceFile, Entity

@pytest.fixture()
def python_source_code():
    return '''
""" top level docs """
import ollama

from stractor.util import logger
from google import genai

default_model = "deepseek-r1:8b"

def get_auto_client(model: str = default_model):
    """Get a client implementation based on the model name."""
	pass

def get_client(model: str = default_model) -> LLM:
    """Get a client implementation based on the model name."""

    if model == "default":
        return LLMOllama()
    elif model.startswith("gemini"):
        return LLMGoogle(model)
    else:
        return LLMOllama()

class LLM:
    """ Interface básica """

    def chat_stream(self, prompt, model_name=default_model, think=False) -> str:
        """ Hello chat_stream """
        pass

    def chat(self, prompt, model_name=default_model, output=None, think=False):
        print('lets chat')
'''

def test_parse_source_code(python_source_code):
    stractor = Stractor()
    res = stractor.parse(python_source_code)

    # Create a mock of 'SourceFile' class using the data from the fixture
    expected_source_file = SourceFile(
        path="",  # No path specified in the fixture
        documentation="top level docs",
        imports=[
            "import ollama",
            "from stractor.util import logger", 
            "from google import genai"
        ],
        top_level_attributes=[
            'default_model = "deepseek-r1:8b"'
        ],
        top_level_functions=[
            Function(
                name="get_auto_client",
                parameters="model: str = default_model",
                return_type=None,
                documentation="Get a client implementation based on the model name.",
                body="pass"
            ),
            Function(
                name="get_client",
                parameters="model: str = default_model",
                return_type="LLM",
                documentation="Get a client implementation based on the model name.",
                body='if model == "default":\n        return LLMOllama()\n    elif model.startswith("gemini"):\n        return LLMGoogle(model)\n    else:\n        return LLMOllama()'
            )
        ],
        entities=[
            Entity(
                name="LLM",
                type="class",
                documentation="Interface básica",
                methods=[
                    Function(
                        name="chat_stream",
                        parameters="self, prompt, model_name=default_model, think=False",
                        return_type="str",
                        documentation="Hello chat_stream",
                        body="pass"
                    ),
                    Function(
                        name="chat",
                        parameters="self, prompt, model_name=default_model, output=None, think=False",
                        return_type=None,
                        documentation=None,
                        body="print('lets chat')"
                    )
                ]
            )
        ]
    )

    # Test assertions
    assert res.documentation == expected_source_file.documentation
    assert sorted(res.imports) == sorted(expected_source_file.imports)
    assert sorted(res.top_level_attributes) == sorted(expected_source_file.top_level_attributes)
    assert len(res.top_level_functions) == len(expected_source_file.top_level_functions)
    assert len(res.entities) == len(expected_source_file.entities)
    
    # Test top-level functions
    for actual_func, expected_func in zip(res.top_level_functions, expected_source_file.top_level_functions):
        assert actual_func.name == expected_func.name
        assert actual_func.parameters == expected_func.parameters
        assert actual_func.return_type == expected_func.return_type
        assert actual_func.documentation == expected_func.documentation
        assert actual_func.body == expected_func.body
    
    # Test entities (classes)
    for actual_entity, expected_entity in zip(res.entities, expected_source_file.entities):
        assert actual_entity.name == expected_entity.name
        assert actual_entity.type == expected_entity.type
        assert actual_entity.documentation == expected_entity.documentation
        assert len(actual_entity.methods) == len(expected_entity.methods)
        
        # Test methods within entities
        for actual_method, expected_method in zip(actual_entity.methods, expected_entity.methods):
            assert actual_method.name == expected_method.name
            assert actual_method.parameters == expected_method.parameters
            assert actual_method.return_type == expected_method.return_type
            assert actual_method.documentation == expected_method.documentation
            assert actual_method.body == expected_method.body
