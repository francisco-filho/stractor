import re
from tree_sitter_language_pack import get_language, get_parser

from stractor.model import Function, Entity, SourceFile


class Stractor:
    """A code structure extractor using Tree-sitter for parsing Python source code."""
    
    def __init__(self):
        self.language = "python"
        self.parser = get_parser(self.language)
        self.lang = get_language(self.language)
        self.contents = None
        self.tree = None
    
    def parse(self, source_code: str, path: str = "") -> SourceFile:
        """Parse Python source code and extract its structure.
        
        Args:
            source_code: The Python source code as a string
            path: Optional file path
            
        Returns:
            A SourceFile object containing the parsed structure
        """
        self.contents = source_code.encode('utf-8')
        self.tree = self.parser.parse(self.contents)
        
        # Extract top-level documentation
        documentation = self._get_module_docstring()
        
        # Extract imports
        imports = self._get_imports()
        
        # Extract top-level attributes
        top_level_attributes = self._get_top_level_attributes()
        
        # Extract top-level functions
        top_level_functions = self._get_module_functions()
        
        # Extract classes/entities
        entities = self._get_classes()
        
        return SourceFile(
            path=path,
            documentation=documentation,
            imports=imports,
            top_level_attributes=top_level_attributes,
            top_level_functions=top_level_functions,
            entities=entities
        )
    
    def _text(self, node):
        """Extracts the text content of a Tree-sitter node.
        
        Args:
            node: The Tree-sitter node.
            
        Returns:
            The decoded string content of the node, or empty string if None.
        """
        if node is None:
            return ""
        return self.contents[node.start_byte:node.end_byte].decode('utf-8')
    
    def _get_node(self, match, key: str):
        """Extracts a specific node from a Tree-sitter match based on a key.
        
        Args:
            match: A Tree-sitter match object.
            key: The key to look for in the match dictionary.
            
        Returns:
            The first node associated with the key, or None if not found.
        """
        match_dict = match[1]
        if key in match_dict:
            return match_dict[key][0]
        return None
    
    def _get_module_docstring(self) -> str | None:
        """Extract the module-level docstring."""
        docstring_scm = """
        (module
            (expression_statement 
                (string) @doc
            )
        )
        """
        
        query = self.lang.query(docstring_scm)
        matches = query.matches(self.tree.root_node)
        
        if matches:
            # Get the first docstring (module docstring)
            first_match = matches[0]
            doc_node = self._get_node(first_match, 'doc')
            if doc_node:
                doc_text = self._text(doc_node)
                # Clean up the docstring by removing quotes and extra whitespace
                doc_text = doc_text.strip('\'"')
                doc_text = doc_text.strip()
                return doc_text if doc_text else None
        
        return None
    
    def _get_imports(self) -> list[str]:
        """Extract import statements from the parsed Python file."""
        imports_scm = """
        (module
            (import_statement)? @import
            (import_from_statement)? @import
            )
        """
        
        query = self.lang.query(imports_scm)
        captures = query.captures(self.tree.root_node)
        
        imports = []
        for node in captures['import']:
            import_text = self._text(node)
            if import_text:
                imports.append(import_text)
        
        return imports
    
    def _get_top_level_attributes(self) -> list[str]:
        """Extract top-level variable assignments from the parsed Python file."""
        attributes_scm = """
        (module
            (expression_statement
                (assignment) @assignment
            )           
        )
        """
        
        query = self.lang.query(attributes_scm)
        captures = query.captures(self.tree.root_node)
        
        attributes = []
        for node in captures['assignment']:
            attr_text = self._text(node)
            if attr_text:
                attributes.append(attr_text)
        
        return attributes
    
    def _get_module_functions(self) -> list[Function]:
        """Extract top-level function definitions."""
        functions_scm = """
        (module
            (function_definition
                name: (identifier) @name
                parameters: (parameters) @params
                return_type: (type)? @return_type
                body: (block) @body
            )
        )
        """
        
        query = self.lang.query(functions_scm)
        matches = query.matches(self.tree.root_node)
        
        functions = []
        for match in matches:
            name = self._text(self._get_node(match, 'name'))
            params = self._text(self._get_node(match, 'params'))
            return_type = self._text(self._get_node(match, 'return_type'))
            body_node = self._get_node(match, 'body')
            
            # Extract docstring and body
            doc, body = self._extract_docstring_and_body(body_node)
            
            # Clean up parameters (remove outer parentheses)
            if params:
                params = params.strip('()')
            
            functions.append(Function(
                name=name,
                parameters=params if params else None,
                return_type=return_type if return_type else None,
                documentation=doc if doc else None,
                body=body if body else None
            ))
        
        return functions
    
    def _get_classes(self) -> list[Entity]:
        """Extract class definitions and their methods."""
        classes_scm = """
        (class_definition
            name: (identifier) @name
            superclasses: (argument_list)? @superclasses
            body: (block
                (expression_statement (string))? @doc
            )
        ) @class_node
        """
        
        query = self.lang.query(classes_scm)
        matches = query.matches(self.tree.root_node)
        
        entities = []
        for match in matches:
            name = self._text(self._get_node(match, 'name'))
            doc = self._text(self._get_node(match, 'doc'))
            class_node = self._get_node(match, 'class_node')
            
            # Clean up docstring
            if doc:
                doc = doc.strip('\'"').strip()
            
            # Extract methods for this class
            methods = self._get_methods_of_class(class_node)
            
            entities.append(Entity(
                name=name,
                type='class',
                documentation=doc if doc else None,
                methods=methods
            ))
        
        return entities
    
    def _get_methods_of_class(self, class_node) -> list[Function]:
        """Extract methods from a given class node."""
        methods_scm = """
        (function_definition
            name: (identifier) @name
            parameters: (parameters) @params
            return_type: (type)? @return_type
            body: (block) @body
        )
        """
        
        query = self.lang.query(methods_scm)
        matches = query.matches(class_node)
        
        methods = []
        for match in matches:
            name = self._text(self._get_node(match, 'name'))
            params = self._text(self._get_node(match, 'params'))
            return_type = self._text(self._get_node(match, 'return_type'))
            body_node = self._get_node(match, 'body')
            
            # Extract docstring and body
            doc, body = self._extract_docstring_and_body(body_node)
            
            # Clean up parameters (remove outer parentheses)
            if params:
                params = params.strip('()')
            
            methods.append(Function(
                name=name,
                parameters=params if params else None,
                return_type=return_type if return_type else None,
                documentation=doc if doc else None,
                body=body if body else None
            ))
        
        return methods
    
    def _extract_docstring_and_body(self, body_node):
        """Extract docstring and body from a function's block node.
        
        Args:
            body_node: The Tree-sitter block node of the function body
            
        Returns:
            Tuple of (docstring, body) where docstring is cleaned and body excludes the docstring
        """
        if not body_node:
            return None, None
        
        full_body_text = self._text(body_node)
        
        # Query to find docstring in the body
        docstring_scm = """
        (block
            (expression_statement 
                (string) @doc
            )
        )
        """
        
        query = self.lang.query(docstring_scm)
        matches = query.matches(body_node)
        
        docstring = None
        body = full_body_text
        
        if matches:
            # Get the first docstring
            first_match = matches[0]
            doc_node = self._get_node(first_match, 'doc')
            if doc_node:
                docstring_text = self._text(doc_node)
                # Clean up the docstring by removing quotes and extra whitespace
                docstring = docstring_text.strip('\'"').strip()
                
                # Remove the docstring from the body
                # Find the docstring in the full body and remove it
                docstring_with_quotes = self._text(doc_node)
                body_lines = full_body_text.split('\n')
                filtered_lines = []
                skip_docstring = False
                
                for line in body_lines:
                    if docstring_with_quotes.strip() in line and not skip_docstring:
                        skip_docstring = True
                        continue
                    if not skip_docstring or line.strip():
                        filtered_lines.append(line)
                        skip_docstring = False
                
                body = '\n'.join(filtered_lines).strip()
        
        # Clean up body - remove outer braces and extra whitespace
        if body:
            body = body.strip()
            if body.startswith('{') and body.endswith('}'):
                body = body[1:-1].strip()
        
        return docstring, body
