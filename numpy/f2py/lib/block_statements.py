"""

"""

import re
import sys

from base_classes import BeginStatement, EndStatement, Statement,\
     AttributeHolder, ProgramBlock
from readfortran import Line
from utils import filter_stmts, parse_bind, parse_result

class HasImplicitStmt:

    a = AttributeHolder(implicit_rules = None)

    def get_type(self, name):
        implicit_rules = self.a.implicit_rules
        if implicit_rules=={}:
            raise ValueError,'Implicit rules mapping is null'
        l = name[0].lower()
        if implicit_rules.has_key(l):
            return implicit_rules[l]
        # default rules
        if l in 'ijklmn':
            return implicit_rules['default_integer']
        return implicit_rules['default_real']

    def initialize(self):
        implicit_rules = self.a.implicit_rules
        if implicit_rules is not None:
            return
        self.a.implicit_rules = implicit_rules = {}
        real = Real(self, self.item.copy('real'))
        assert real.isvalid
        integer = Integer(self, self.item.copy('integer'))
        assert integer.isvalid
        implicit_rules['default_real'] = real
        implicit_rules['default_integer'] = integer
        return

class HasUseStmt:

    a = AttributeHolder(use = {})

    def get_entity(self, name):
        for modname, modblock in self.top.a.module.items():
            for stmt in modblock.content:
                if getattr(stmt,'name','') == name:
                    return stmt
        return
    
    def initialize(self):
        
        return

class HasVariables:

    a = AttributeHolder(variables = {})

class HasTypeDecls:

    a = AttributeHolder(type_decls = {})

class HasAttributes:

    a = AttributeHolder(attributes = [])

class HasModuleProcedures:

    a = AttributeHolder(module_procedures = [])

# File block

class EndSource(EndStatement):
    """
    Dummy End statement for BeginSource.
    """
    match = staticmethod(lambda s: False)

class BeginSource(BeginStatement):
    """
    Fortran source content.
    """
    match = staticmethod(lambda s: True)
    end_stmt_cls = EndSource
    a = AttributeHolder(module = {},
                        external_subprogram = {},
                        blockdata = {},
                        )

    def tostr(self):
        return '!' + self.blocktype.upper() + ' '+ self.name

    def process_item(self):
        self.name = self.reader.name
        self.top = self
        self.fill(end_flag = True)
        return

    def analyze(self):
        for stmt in self.content:
            if isinstance(stmt, Module):
                stmt.analyze()
                self.a.module[stmt.name] = stmt
            elif isinstance(stmt, SubProgramStatement):
                stmt.analyze()
                self.a.external_subprogram[stmt.name] = stmt
            elif isinstance(stmt, BlockData):
                stmt.analyze()
                self.a.blockdata[stmt.name] = stmt
            else:
                stmt.analyze()
        return

    def get_classes(self):
        return program_unit

    def process_subitem(self, item):
        # MAIN block does not define start/end line conditions,
        # so it should never end until all lines are read.
        # However, sometimes F77 programs lack the PROGRAM statement,
        # and here we fix that:
        if self.reader.isfix77:
            line = item.get_line()
            if line=='end':
                message = item.reader.format_message(\
                        'WARNING',
                        'assuming the end of undefined PROGRAM statement',
                        item.span[0],item.span[1])
                print >> sys.stderr, message
                p = Program(self)
                p.content.extend(self.content)
                p.content.append(EndProgram(p,item))
                self.content[:] = [p]
                return
        return BeginStatement.process_subitem(self, item)

# Module

class EndModule(EndStatement):
    match = re.compile(r'end(\s*module\s*\w*|)\Z', re.I).match

class Module(BeginStatement, HasAttributes,
             HasImplicitStmt, HasUseStmt, HasVariables,
             HasTypeDecls):
    """
    MODULE <name>
     ..
    END [MODULE [name]]
    """
    match = re.compile(r'module\s*\w+\Z', re.I).match
    end_stmt_cls = EndModule
    a = AttributeHolder(module_subprogram = {},
                        module_data = {},
                        )

    def get_classes(self):
        return access_spec + specification_part + module_subprogram_part

    def process_item(self):
        name = self.item.get_line().replace(' ','')[len(self.blocktype):].strip()
        self.name = name
        return BeginStatement.process_item(self)

    def analyze(self):
        content = self.content[:]

        [stmt.analyze() for stmt in filter_stmts(content, Use)]
        HasUseStmt.initialize(self)

        [stmt.analyze() for stmt in filter_stmts(content, Implicit)]
        HasImplicitStmt.initialize(self)

        while content:
            stmt = content.pop(0)
            if isinstance(stmt, Contains):
                for stmt in filter_stmts(content, SubProgramStatement):
                    stmt.analyze()
                    self.a.module_subprogram[stmt.name] = stmt
                stmt = content.pop(0)
                assert isinstance(stmt, EndModule),`stmt`
                continue
            stmt.analyze()

        if content:
            self.show_message('Not analyzed content: %s' % content)

        return

# Python Module

class EndPythonModule(EndStatement):
    match = re.compile(r'end(\s*python\s*module\s*\w*|)\Z', re.I).match

class PythonModule(BeginStatement, HasImplicitStmt, HasUseStmt):
    """
    PYTHON MODULE <name>
     ..
    END [PYTHON MODULE [name]]
    """
    modes = ['pyf']
    match = re.compile(r'python\s*module\s*\w+\Z', re.I).match
    end_stmt_cls = EndPythonModule

    def get_classes(self):
        return [Interface, Function, Subroutine, Module]

    def process_item(self):
        self.name = self.item.get_line().replace(' ','')\
                    [len(self.blocktype):].strip()
        return BeginStatement.process_item(self)

# Program

class EndProgram(EndStatement):
    """
    END [PROGRAM [name]]
    """
    match = re.compile(r'end(\s*program\s*\w*|)\Z', re.I).match

class Program(BeginStatement, ProgramBlock, HasAttributes,
              HasImplicitStmt, HasUseStmt):
    """ PROGRAM [name]
    """
    match = re.compile(r'program\s*\w*\Z', re.I).match
    end_stmt_cls = EndProgram

    def get_classes(self):
        return specification_part + execution_part + internal_subprogram_part

    def process_item(self):
        if self.item is not None:
            name = self.item.get_line().replace(' ','')\
                   [len(self.blocktype):].strip()
            if name:
                self.name = name
        return BeginStatement.process_item(self)

# BlockData

class EndBlockData(EndStatement):
    """
    END [ BLOCK DATA [ <block-data-name> ] ] 
    """
    match = re.compile(r'end(\s*block\s*data\s*\w*|)\Z', re.I).match
    blocktype = 'blockdata'

class BlockData(BeginStatement, HasImplicitStmt, HasUseStmt,
                HasVariables):
    """
    BLOCK DATA [ <block-data-name> ]
    """
    end_stmt_cls = EndBlockData
    match = re.compile(r'block\s*data\s*\w*\Z', re.I).match

    def process_item(self):
        self.name = self.item.get_line()[5:].lstrip()[4:].lstrip()
        return BeginStatement.process_item(self)

    def get_classes(self):
        return specification_part
        
# Interface

class EndInterface(EndStatement):
    match = re.compile(r'end\s*interface\s*\w*\Z', re.I).match
    blocktype = 'interface'

class Interface(BeginStatement, HasImplicitStmt, HasUseStmt,
                HasModuleProcedures
                ):
    """
    INTERFACE [<generic-spec>] | ABSTRACT INTERFACE
    END INTERFACE [<generic-spec>]

    <generic-spec> = <generic-name>
                   | OPERATOR ( <defined-operator> )
                   | ASSIGNMENT ( = )
                   | <dtio-generic-spec>
    <dtio-generic-spec> = READ ( FORMATTED )
                        | READ ( UNFORMATTED )
                        | WRITE ( FORMATTED )
                        | WRITE ( UNFORMATTED )
    
    """
    modes = ['free90', 'fix90', 'pyf']
    match = re.compile(r'(interface\s*(\w+\s*\(.*\)|\w*)|abstract\s*interface)\Z',re.I).match
    end_stmt_cls = EndInterface
    blocktype = 'interface'

    def get_classes(self):
        return intrinsic_type_spec + interface_specification

    def process_item(self):
        line = self.item.get_line()
        self.isabstract = line.startswith('abstract')
        if self.isabstract:
            self.generic_spec = ''
        else:
            self.generic_spec = line[len(self.blocktype):].strip()
        self.name = self.generic_spec # XXX
        return BeginStatement.process_item(self)

    def tostr(self):
        if self.isabstract:
            return 'ABSTRACT INTERFACE'
        return 'INTERFACE '+ str(self.generic_spec)


# Subroutine

class SubProgramStatement(BeginStatement, ProgramBlock,
                          HasImplicitStmt, HasAttributes,
                          HasUseStmt, HasVariables, HasTypeDecls
                          ):
    """
    [ <prefix> ] <FUNCTION|SUBROUTINE> <name> [ ( <args> ) ] [ <suffix> ]
    """
    a = AttributeHolder(internal_subprogram = {})

    def process_item(self):
        clsname = self.__class__.__name__.lower()
        item = self.item
        line = item.get_line()
        m = self.match(line)
        i = line.find(clsname)
        assert i!=-1,`line`
        self.prefix = line[:i].rstrip()
        self.name = line[i:m.end()].lstrip()[len(clsname):].strip()
        line = line[m.end():].lstrip()
        args = []
        if line.startswith('('):
            i = line.find(')')
            assert i!=-1,`line`
            line2 = item.apply_map(line[:i+1])
            for a in line2[1:-1].split(','):
                a=a.strip()
                if not a: continue
                args.append(a)
            line = line[i+1:].lstrip()
        suffix = item.apply_map(line)
        self.bind, suffix = parse_bind(suffix, item)
        self.result = None
        if isinstance(self, Function):
            self.result, suffix = parse_result(suffix, item)
            if suffix:
                assert self.bind is None,`self.bind`
                self.bind, suffix = parse_result(suffix, item)
            if self.result is None:
                self.result = self.name
        assert not suffix,`suffix`
        self.args = args
        self.typedecl = None
        return BeginStatement.process_item(self)

    def tostr(self):
        clsname = self.__class__.__name__.upper()
        s = ''
        if self.prefix:
            s += self.prefix + ' '
        if self.typedecl is not None:
            assert isinstance(self, Function),`self.__class__.__name__`
            s += self.typedecl.tostr() + ' '
        s += clsname
        suf = ''
        if self.result and self.result!=self.name:
            suf += ' RESULT ( %s )' % (self.result)
        if self.bind:
            suf += ' BIND ( %s )' % (', '.join(self.bind))
        return '%s %s(%s)%s' % (s, self.name,', '.join(self.args),suf)

    def get_classes(self):
        return f2py_stmt + specification_part + execution_part \
               + internal_subprogram_part

    def analyze(self):
        content = self.content[:]

        variables = self.a.variables
        for a in self.args:
            assert not variables.has_key(a)
            assert is_name(a)
            variables[a] = Variable(self, a)

        if isinstance(self, Function):
            variables[self.result] = Variable(self, self.result)

        [stmt.analyze() for stmt in filter_stmts(content, Use)]
        HasUseStmt.initialize(self)

        [stmt.analyze() for stmt in filter_stmts(content, Implicit)]
        HasImplicitStmt.initialize(self)

        while content:
            stmt = content.pop(0)
            if isinstance(stmt, Contains):
                for stmt in filter_stmts(content, SubProgramStatement):
                    stmt.analyze()
                    self.a.internal_subprogram[stmt.name] = stmt
                stmt = content.pop(0)
                assert isinstance(stmt, self.end_stmt_cls),`stmt`
            elif isinstance(stmt, self.end_stmt_cls):
                continue
            else:
                stmt.analyze()
        if content:
            self.show_message('Not analyzed content: %s' % content)

        return

class EndSubroutine(EndStatement):
    """
    END [SUBROUTINE [name]]
    """
    match = re.compile(r'end(\s*subroutine\s*\w*|)\Z', re.I).match


class Subroutine(SubProgramStatement):
    """
    [ <prefix> ] SUBROUTINE <name> [ ( [ <dummy-arg-list> ] ) [ <proc-language-binding-spec> ]]
    """
    end_stmt_cls = EndSubroutine
    match = re.compile(r'(recursive|pure|elemental|\s)*subroutine\s*\w+', re.I).match

# Function

class EndFunction(EndStatement):
    """
    END [FUNCTION [name]]
    """
    match = re.compile(r'end(\s*function\s*\w*|)\Z', re.I).match

class Function(SubProgramStatement):
    """
    [ <prefix> ] FUNCTION <name> ( [<dummy-arg-list>] ) [<suffix>]
    <prefix> = <prefix-spec> [ <prefix-spec> ]...
    <prefix-spec> = <declaration-type-spec>
                  | RECURSIVE | PURE | ELEMENTAL
    <suffix> = <proc-language-binding-spec> [ RESULT ( <result-name> ) ]
             | RESULT ( <result-name> ) [ <proc-language-binding-spec> ]
    """
    end_stmt_cls = EndFunction
    match = re.compile(r'(recursive|pure|elemental|\s)*function\s*\w+', re.I).match

# Handle subprogram prefixes

class SubprogramPrefix(Statement):
    """
    <prefix> <declaration-type-spec> <function|subroutine> ...
    """
    match = re.compile(r'(pure|elemental|recursive|\s)+\b',re.I).match
    def process_item(self):
        line = self.item.get_line()
        m = self.match(line)
        prefix = line[:m.end()].rstrip()
        rest = self.item.get_line()[m.end():].lstrip()
        if rest:
            self.parent.put_item(self.item.copy(prefix))
            self.item.clone(rest)
            self.isvalid = False
            return
        if self.parent.__class__ not in [Function, Subroutine]:
            self.isvalid = False
            return
        prefix = prefix + ' ' + self.parent.prefix
        self.parent.prefix = prefix.strip()
        self.ignore = True
        return

# SelectCase

class EndSelect(EndStatement):
    match = re.compile(r'end\s*select\s*\w*\Z', re.I).match
    blocktype = 'select'

class Select(BeginStatement):
    """
    [ <case-construct-name> : ] SELECT CASE ( <case-expr> )
    
    """
    match = re.compile(r'select\s*case\s*\(.*\)\Z',re.I).match
    end_stmt_cls = EndSelect
    name = ''
    def tostr(self):
        return 'SELECT CASE ( %s )' % (self.expr)
    def process_item(self):
        self.expr = self.item.get_line()[6:].lstrip()[4:].lstrip()[1:-1].strip()
        self.name = self.item.label                
        return BeginStatement.process_item(self)

    def get_classes(self):
        return [Case] + execution_part_construct

# Where

class EndWhere(EndStatement):
    """
    END WHERE [ <where-construct-name> ]
    """
    match = re.compile(r'end\s*\where\s*\w*\Z',re.I).match
    

class Where(BeginStatement):
    """
    [ <where-construct-name> : ] WHERE ( <mask-expr> )
    <mask-expr> = <logical-expr>
    """
    match = re.compile(r'where\s*\([^)]*\)\Z',re.I).match
    end_stmt_cls = EndWhere
    name = ''
    def tostr(self):
        return 'WHERE ( %s )' % (self.expr)
    def process_item(self):
        self.expr = self.item.get_line()[5:].lstrip()[1:-1].strip()
        self.name = self.item.label
        return BeginStatement.process_item(self)

    def get_classes(self):
        return [Assignment, WhereStmt,
                WhereConstruct, ElseWhere
                ]

WhereConstruct = Where

# Forall

class EndForall(EndStatement):
    """
    END FORALL [ <forall-construct-name> ]
    """
    match = re.compile(r'end\s*forall\s*\w*\Z',re.I).match
    
class Forall(BeginStatement):
    """
    [ <forall-construct-name> : ] FORALL <forall-header>
      [ <forall-body-construct> ]...
    <forall-body-construct> = <forall-assignment-stmt>
                            | <where-stmt>
                            | <where-construct>
                            | <forall-construct>
                            | <forall-stmt>
    <forall-header> = ( <forall-triplet-spec-list> [ , <scalar-mask-expr> ] )
    <forall-triplet-spec> = <index-name> = <subscript> : <subscript> [ : <stride> ]
    <subscript|stride> = <scalar-int-expr>
    <forall-assignment-stmt> = <assignment-stmt> | <pointer-assignment-stmt>
    """
    end_stmt_cls = EndForall
    match = re.compile(r'forarr\s*\(.*\)\Z',re.I).match
    name = ''
    def process_item(self):
        self.specs = self.item.get_line()[6:].lstrip()[1:-1].strip()
        return BeginStatement.process_item(self)
    def tostr(self):
        return 'FORALL (%s)' % (self.specs)
    def get_classes(self):
        return [GeneralAssignment, WhereStmt, WhereConstruct,
                ForallConstruct, ForallStmt]

ForallConstruct = Forall

# IfThen

class EndIfThen(EndStatement):
    """
    END IF [ <if-construct-name> ]
    """
    match = re.compile(r'end\s*if\s*\w*\Z', re.I).match
    blocktype = 'if'

class IfThen(BeginStatement):
    """
    [<if-construct-name> :] IF ( <scalar-logical-expr> ) THEN

    IfThen instance has the following attributes:
      expr
    """

    match = re.compile(r'if\s*\(.*\)\s*then\Z',re.I).match
    end_stmt_cls = EndIfThen
    name = ''

    def tostr(self):
        return 'IF (%s) THEN' % (self.expr)

    def process_item(self):
        item = self.item
        line = item.get_line()[2:-4].strip()
        assert line[0]=='(' and line[-1]==')',`line`
        self.expr = line[1:-1].strip()
        self.name = item.label
        return BeginStatement.process_item(self)
        
    def get_classes(self):
        return [Else, ElseIf] + execution_part_construct

class If(BeginStatement):
    """
    IF ( <scalar-logical-expr> ) action-stmt
    """

    match = re.compile(r'if\s*\(').match

    def process_item(self):
        item = self.item
        mode = self.reader.mode
        classes = self.get_classes()
        classes = [cls for cls in classes if mode in cls.modes]

        line = item.get_line()[2:]
        i = line.find(')')
        expr = line[1:i].strip()
        line = line[i+1:].strip()
        if line.lower()=='then':
            self.isvalid = False
            return
        self.expr = expr[1:-1]

        if not line:
            newitem = self.get_item()
        else:
            newitem = item.copy(line)
        newline = newitem.get_line()
        for cls in classes:
            if cls.match(newline):
                stmt = cls(self, newitem)
                if stmt.isvalid:
                    self.content.append(stmt)
                    return
        if not line:
            self.put_item(newitem)
        self.isvalid = False
        return
        
    def tostr(self):
        assert len(self.content)==1,`self.content`
        return 'IF (%s) %s' % (self.expr, str(self.content[0]).lstrip())

    def __str__(self):
        return self.get_indent_tab(colon=':') + self.tostr()

    def get_classes(self):
        return action_stmt

# Do

class EndDo(EndStatement):
    """
    END DO [ <do-construct-name> ]
    """
    match = re.compile(r'end\s*do\s*\w*\Z', re.I).match
    blocktype = 'do'

class Do(BeginStatement):
    """
    [ <do-construct-name> : ] DO label [loopcontrol]
    [ <do-construct-name> : ] DO [loopcontrol]

    """

    match = re.compile(r'do\b\s*\d*',re.I).match
    item_re = re.compile(r'do\b\s*(?P<label>\d*)\s*,?\s*(?P<loopcontrol>.*)\Z',re.I).match
    end_stmt_cls = EndDo
    name = ''

    def tostr(self):
        return 'DO %s %s' % (self.endlabel, self.loopcontrol)

    def process_item(self):
        item = self.item
        line = item.get_line()
        m = self.item_re(line)
        self.endlabel = m.group('label').strip()
        self.name = item.label
        self.loopcontrol = m.group('loopcontrol').strip()
        return BeginStatement.process_item(self)

    def process_subitem(self, item):
        r = False
        if self.endlabel:
            label = item.label
            if label == self.endlabel:
                r = True
                if isinstance(self.parent, Do) and label==self.parent.endlabel:
                    # the same item label may be used for different block ends
                    self.put_item(item)
        return BeginStatement.process_subitem(self, item) or r

    def get_classes(self):
        return execution_part_construct

# Associate

class EndAssociate(EndStatement):
    """
    END ASSOCIATE [ <associate-construct-name> ]
    """
    match = re.compile(r'end\s*associate\s*\w*\Z',re.I).match

class Associate(BeginStatement):
    """
    [ <associate-construct-name> : ] ASSOCIATE ( <association-list> )
      <block>

    <association> = <associate-name> => <selector>
    <selector> = <expr> | <variable>
    """
    match = re.compile(r'associate\s*\(.*\)\Z',re.I).match
    end_stmt_cls = EndAssociate
    
    def process_item(self):
        line = self.item.get_line()[9:].lstrip()
        self.associations = line[1:-1].strip()
        return BeginStatement.process_item(self)
    def tostr(self):
        return 'ASSOCIATE (%s)' % (self.associations)
    def get_classes(self):
        return execution_part_construct

# Type

class EndType(EndStatement):
    """
    END TYPE [<type-name>]
    """
    match = re.compile(r'end\s*type\s*\w*\Z', re.I).match
    blocktype = 'type'

class Type(BeginStatement, HasVariables, HasAttributes):
    """
    TYPE [ [, <type-attr-spec-list>] ::] <type-name> [ ( <type-param-name-list> ) ]
    <type-attr-spec> = <access-spec> | EXTENDS ( <parent-type-name> )
                       | ABSTRACT | BIND(C)
    """
    match = re.compile(r'type\b\s*').match
    end_stmt_cls = EndType
    is_name = re.compile(r'\w+\Z').match

    def process_item(self):
        line = self.item.get_line()[4:].lstrip()
        if line.startswith('('):
            self.isvalid = False
            return
        specs = []
        i = line.find('::')
        if i!=-1:
            for s in line[:i].split(','):
                s = s.strip()
                if s: specs.append(s)
            line = line[i+2:].lstrip()
        self.specs = specs
        i = line.find('(')
        if i!=-1:
            self.name = line[:i].rstrip()
            assert line[-1]==')',`line`
            self.params = line[i+1:-1].lstrip()
        else:
            self.name = line
            self.params = ''
        if not self.is_name(self.name):
            self.isvalid = False
            return
        return BeginStatement.process_item(self)

    def tostr(self):
        s = 'TYPE'
        if self.specs:
            s += ', '.join(['']+self.specs) + ' ::'
        s += ' ' + self.name
        if self.params:
            s += ' ('+self.params+')'
        return s

    def get_classes(self):
        return [Integer] + private_or_sequence + component_part +\
               type_bound_procedure_part

    def analyze(self):
        BeginStatement.analyze(self)
        assert isinstance(self.parent,HasTypeDecls)
        self.parent.a.type_decls[self.name] = self
        return

TypeDecl = Type

# Enum

class EndEnum(EndStatement):
    """
    END ENUM
    """
    match = re.compile(r'end\s*enum\Z',re.I).match
    blocktype = 'enum'

class Enum(BeginStatement):
    """
    ENUM , BIND(C)
      <enumerator-def-stmt>
      [ <enumerator-def-stmt> ]...
    """
    blocktype = 'enum'
    end_stmt_cls = EndEnum
    match = re.compile(r'enum\s*,\s*bind\s*\(\s*c\s*\)\Z',re.I).match
    def process_item(self):
        return BeginStatement.process_item(self)
    def get_classes(self):
        return [Enumerator]

###################################################

from statements import *
from typedecl_statements import *

f2py_stmt = [Threadsafe, FortranName, Depend, Check, CallStatement,
             CallProtoArgument]

access_spec = [Public, Private]

interface_specification = [Function, Subroutine,
                           ModuleProcedure
                           ]

module_subprogram_part = [ Contains, Function, Subroutine ]

specification_stmt = access_spec + [ Allocatable, Asynchronous, Bind,
    Common, Data, Dimension, Equivalence, External, Intent, Intrinsic,
    Namelist, Optional, Pointer, Protected, Save, Target, Volatile,
    Value ]

intrinsic_type_spec = [ SubprogramPrefix, Integer , Real,
    DoublePrecision, Complex, DoubleComplex, Character, Logical, Byte
    ]

derived_type_spec = [  ]
type_spec = intrinsic_type_spec + derived_type_spec
declaration_type_spec = intrinsic_type_spec + [ TypeStmt, Class ]
    
type_declaration_stmt = declaration_type_spec

private_or_sequence = [ Private, Sequence ]

component_part = declaration_type_spec + [ ModuleProcedure ]

proc_binding_stmt = [SpecificBinding, GenericBinding, FinalBinding]

type_bound_procedure_part = [Contains, Private] + proc_binding_stmt

#R214
action_stmt = [ Allocate, GeneralAssignment, Assign, Backspace, Call, Close,
    Continue, Cycle, Deallocate, Endfile, Exit, Flush, ForallStmt,
    Goto, If, Inquire, Nullify, Open, Print, Read, Return, Rewind,
    Stop, Wait, WhereStmt, Write, ArithmeticIf, ComputedGoto,
    AssignedGoto, Pause ]
# GeneralAssignment = Assignment + PointerAssignment
# EndFunction, EndProgram, EndSubroutine - part of the corresponding blocks

executable_construct = [ Associate, Do, ForallConstruct, IfThen,
    Select, WhereConstruct ] + action_stmt
#Case, see Select

execution_part_construct = executable_construct + [ Format, Entry,
    Data ]

execution_part = execution_part_construct[:]

#C201, R208
for cls in [EndFunction, EndProgram, EndSubroutine]:
    try: execution_part.remove(cls)
    except ValueError: pass

internal_subprogram = [Function, Subroutine]

internal_subprogram_part = [ Contains, ] + internal_subprogram

declaration_construct = [ TypeDecl, Entry, Enum, Format, Interface,
    Parameter, ModuleProcedure, ] + specification_stmt + \
    type_declaration_stmt
# stmt-function-stmt

implicit_part = [ Implicit, Parameter, Format, Entry ]

specification_part = [ Use, Import ] + implicit_part + \
                     declaration_construct


external_subprogram = [Function, Subroutine]

main_program = [Program] + specification_part + execution_part + \
               internal_subprogram_part

program_unit = main_program + external_subprogram + [Module,
                                                     BlockData ]
