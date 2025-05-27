
import re
import logging
from typing import List, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    def __init__(self):
        self.patterns = self._load_analysis_patterns()
    
    def _load_analysis_patterns(self) -> Dict[str, List[Dict]]:
        """Load code analysis patterns for different languages"""
        return {
             python : [
                {
                     type :  Security ,
                     pattern : r eval\s*\( ,
                     description :  Use of eval() function can be dangerous ,
                     severity :  high 
                },
                {
                     type :  Security ,
                     pattern : r exec\s*\( ,
                     description :  Use of exec() function can be dangerous ,
                     severity :  high 
                },
                {
                     type :  Best Practice ,
                     pattern : r except\s*: ,
                     description :  Bare except clause catches all exceptions ,
                     severity :  medium 
                },
                {
                     type :  Code Quality ,
                     pattern : r print\s*\( ,
                     description :  Consider using logging instead of print statements ,
                     severity :  low 
                },
                {
                     type :  Security ,
                     pattern : r shell\s*=\s*True ,
                     description :  subprocess with shell=True can be dangerous ,
                     severity :  high 
                }
            ],
             javascript : [
                {
                     type :  Security ,
                     pattern : r eval\s*\( ,
                     description :  Use of eval() function can be dangerous ,
                     severity :  high 
                },
                {
                     type :  Best Practice ,
                     pattern : r var\s+\w+ ,
                     description :  Consider using let or const instead of var ,
                     severity :  medium 
                },
                {
                     type :  Security ,
                     pattern : r innerHTML\s*= ,
                     description :  Direct innerHTML assignment can lead to XSS ,
                     severity :  high 
                },
                {
                     type :  Code Quality ,
                     pattern : r console\.log\s*\( ,
                     description :  Remove console.log statements in production ,
                     severity :  low 
                }
            ],
             sql : [
                {
                     type :  Security ,
                     pattern : r SELECT\s+.*\+.*FROM ,
                     description :  Potential SQL injection vulnerability ,
                     severity :  critical 
                },
                {
                     type :  Security ,
                     pattern : r INSERT\s+.*\+.*VALUES ,
                     description :  Potential SQL injection vulnerability ,
                     severity :  critical 
                },
                {
                     type :  Security ,
                     pattern : r UPDATE\s+.*\+.*SET ,
                     description :  Potential SQL injection vulnerability ,
                     severity :  critical 
                }
            ],
             general : [
                {
                     type :  Security ,
                     pattern : r password\s*=\s*["\ ][^"\ ]+["\ ] ,
                     description :  Hardcoded password detected ,
                     severity :  critical 
                },
                {
                     type :  Security ,
                     pattern : r api_key\s*=\s*["\ ][^"\ ]+["\ ] ,
                     description :  Hardcoded API key detected ,
                     severity :  critical 
                },
                {
                     type :  Security ,
                     pattern : r secret\s*=\s*["\ ][^"\ ]+["\ ] ,
                     description :  Hardcoded secret detected ,
                     severity :  critical 
                },
                {
                     type :  Best Practice ,
                     pattern : r TODO|FIXME|HACK ,
                     description :  TODO/FIXME comment found ,
                     severity :  low 
                }
            ]
        }
    
    async def analyze_file(self, filename: str, content: str, file_extension: str) -> List[Dict[str, Any]]:
        """Analyze a single file for code issues"""
        issues = []
        
        try:
            # Determine language patterns to use
            language_patterns = []
            
            if file_extension in [ py ]:
                language_patterns.extend(self.patterns.get( python , []))
            elif file_extension in [ js ,  jsx ,  ts ,  tsx ]:
                language_patterns.extend(self.patterns.get( javascript , []))
            elif file_extension in [ sql ]:
                language_patterns.extend(self.patterns.get( sql , []))
            
            # Always apply general patterns
            language_patterns.extend(self.patterns.get( general , []))
            
            # Analyze content line by line
            lines = content.split( \n )
            for line_num, line in enumerate(lines, 1):
                line_issues = self._analyze_line(line, line_num, filename, language_patterns)
                issues.extend(line_issues)
            
            # Perform file-level analysis
            file_level_issues = await self._analyze_file_structure(filename, content, file_extension)
            issues.extend(file_level_issues)
            
        except Exception as e:
            logger.error(f"Error analyzing file {filename}: {str(e)}")
            issues.append({
                 type :  Analysis Error ,
                 description : f Could not fully analyze file: {str(e)} ,
                 severity :  low ,
                 line : 0,
                 file : filename
            })
        
        return issues
    
    def _analyze_line(self, line: str, line_num: int, filename: str, patterns: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze a single line of code"""
        issues = []
        
        for pattern_info in patterns:
            try:
                if re.search(pattern_info[ pattern ], line, re.IGNORECASE):
                    issues.append({
                         type : pattern_info[ type ],
                         description : pattern_info[ description ],
                         severity : pattern_info[ severity ],
                         line : line_num,
                         file : filename,
                         code_snippet : line.strip()
                    })
            except re.error as e:
                logger.warning(f"Invalid regex pattern {pattern_info[ pattern ]}: {str(e)}")
                continue
        
        return issues
    
    async def _analyze_file_structure(self, filename: str, content: str, file_extension: str) -> List[Dict[str, Any]]:
        """Perform file-level structural analysis"""
        issues = []
        
        try:
            # Check file size
            if len(content) > 50000:  # 50KB
                issues.append({
                     type :  Code Quality ,
                     description :  Large file size - consider splitting into smaller modules ,
                     severity :  medium ,
                     line : 0,
                     file : filename
                })
            
            # Check line length
            lines = content.split( \n )
            long_lines = [(i+1, line) for i, line in enumerate(lines) if len(line) > 120]
            
            if long_lines:
                for line_num, line in long_lines[:5]:  # Report first 5 long lines
                    issues.append({
                         type :  Code Quality ,
                         description : f Line too long ({len(line)} characters) ,
                         severity :  low ,
                         line : line_num,
                         file : filename,
                         code_snippet : line[:100] +  ...  if len(line) > 100 else line
                    })
            
            # Language-specific structural checks
            if file_extension ==  py :
                python_issues = await self._analyze_python_structure(filename, content)
                issues.extend(python_issues)
            elif file_extension in [ js ,  jsx ,  ts ,  tsx ]:
                js_issues = await self._analyze_javascript_structure(filename, content)
                issues.extend(js_issues)
            
        except Exception as e:
            logger.error(f"Error in structural analysis for {filename}: {str(e)}")
        
        return issues
    
    async def _analyze_python_structure(self, filename: str, content: str) -> List[Dict[str, Any]]:
        """Analyze Python-specific structure"""
        issues = []
        
        try:
            lines = content.split( \n )
            
            # Check for missing docstrings in functions/classes
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Check for function definitions
                if stripped.startswith( def  ) and not stripped.startswith( def _ ):
                    # Check if next non-empty line is a docstring
                    next_line_idx = i + 1
                    while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                        next_line_idx += 1
                    
                    if (next_line_idx >= len(lines) or 
                        not lines[next_line_idx].strip().startswith( """ ) and 
                        not lines[next_line_idx].strip().startswith("   ")):
                        issues.append({
                             type :  Best Practice ,
                             description :  Public function missing docstring ,
                             severity :  low ,
                             line : i + 1,
                             file : filename,
                             code_snippet : stripped
                        })
                
                # Check for class definitions
                if stripped.startswith( class  ):
                    # Similar docstring check for classes
                    next_line_idx = i + 1
                    while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                        next_line_idx += 1
                    
                    if (next_line_idx >= len(lines) or 
                        not lines[next_line_idx].strip().startswith( """ ) and 
                        not lines[next_line_idx].strip().startswith("   ")):
                        issues.append({
                             type :  Best Practice ,
                             description :  Class missing docstring ,
                             severity :  low ,
                             line : i + 1,
                             file : filename,
                             code_snippet : stripped
                        })
            
            # Check imports
            import_issues = self._check_python_imports(content, filename)
            issues.extend(import_issues)
            
        except Exception as e:
            logger.error(f"Error in Python structural analysis: {str(e)}")
        
        return issues
    
    async def _analyze_javascript_structure(self, filename: str, content: str) -> List[Dict[str, Any]]:
        """Analyze JavaScript-specific structure"""
        issues = []
        
        try:
            # Check for missing semicolons
            lines = content.split( \n )
            for i, line in enumerate(lines):
                stripped = line.strip()
                if (stripped and 
                    not stripped.endswith( ; ) and 
                    not stripped.endswith( { ) and 
                    not stripped.endswith( } ) and
                    not stripped.startswith( // ) and
                    not stripped.startswith( /* ) and
                    not stripped.startswith( * ) and
                    re.match(r ^(var|let|const|return|\w+\s*=) , stripped)):
                    
                    issues.append({
                         type :  Code Quality ,
                         description :  Missing semicolon ,
                         severity :  low ,
                         line : i + 1,
                         file : filename,
                         code_snippet : stripped
                    })
            
        except Exception as e:
            logger.error(f"Error in JavaScript structural analysis: {str(e)}")
        
        return issues
    
    def _check_python_imports(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """Check Python imports for issues"""
        issues = []
        
        try:
            lines = content.split( \n )
            import_lines = []
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith( import  ) or stripped.startswith( from  ):
                    import_lines.append((i + 1, stripped))
            
            # Check for unused imports (basic check)
            for line_num, import_line in import_lines:
                if  import *  in import_line:
                    issues.append({
                         type :  Best Practice ,
                         description :  Avoid wildcard imports (import *) ,
                         severity :  medium ,
                         line : line_num,
                         file : filename,
                         code_snippet : import_line
                    })
            
        except Exception as e:
            logger.error(f"Error checking Python imports: {str(e)}")
        
        return issues
