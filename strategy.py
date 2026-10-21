"""Small, safe strategy language: no eval() or execution of user Python."""
from dataclasses import dataclass
import re
import difflib

TOKEN = re.compile(r'\s*(>=|<=|==|!=|[()<>]|\bAND\b|\bOR\b|\bNOT\b|[A-Za-z_][A-Za-z_0-9]*|\d+(?:\.\d+)?)', re.I)

class StrategyError(ValueError):
    pass

@dataclass
class Node:
    op: str
    a: object
    b: object = None

class Parser:
    def __init__(self, text):
        self.tokens = []
        pos = 0
        while pos < len(text):
            if not text[pos:].strip():
                break
            m = TOKEN.match(text, pos)
            if not m:
                raise StrategyError(f'Unrecognised token at column {pos + 1}: {text[pos:pos+12]!r}')
            self.tokens.append(m.group(1).upper())
            pos = m.end()
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self, expected=None):
        t = self.peek()
        if t is None or (expected is not None and t != expected):
            raise StrategyError(f'Expected {expected or "expression"}, found {t or "end of line"}')
        self.pos += 1
        return t

    def parse(self):
        out = self.logic_or()
        if self.peek() is not None:
            raise StrategyError(f'Unexpected token {self.peek()!r}')
        return out

    def logic_or(self):
        a = self.logic_and()
        while self.peek() == 'OR':
            self.take(); a = Node('OR', a, self.logic_and())
        return a

    def logic_and(self):
        a = self.logic_not()
        while self.peek() == 'AND':
            self.take(); a = Node('AND', a, self.logic_not())
        return a

    def logic_not(self):
        if self.peek() == 'NOT':
            self.take(); return Node('NOT', self.logic_not())
        if self.peek() == '(':
            self.take('('); a = self.logic_or(); self.take(')'); return a
        left = self.value()
        op = self.take()
        if op not in ('<', '>', '<=', '>=', '==', '!='):
            raise StrategyError(f'Expected comparison operator, found {op!r}')
        return Node(op, left, self.value())

    def value(self):
        t = self.take()
        if re.fullmatch(r'\d+(?:\.\d+)?', t):
            return Node('CONST', float(t))
        if t in ('CLOSE', 'RSI', 'MACD', 'MACD_SIGNAL', 'VOLUME') or re.fullmatch(r'SMA_[1-9]\d*|RSI_[1-9]\d*|VOLUME_SMA_[1-9]\d*', t):
            return Node('FIELD', t)
        options=['CLOSE','RSI','RSI_14','SMA_20','SMA_50','MACD','MACD_SIGNAL','VOLUME','VOLUME_SMA_20']
        suggestion=difflib.get_close_matches(t,options,n=1,cutoff=.5)
        note=f" Did you mean {suggestion[0]}?" if suggestion else ''
        raise StrategyError(f'Unknown indicator {t!r}.{note} Supported examples: RSI, SMA_50, MACD, VOLUME_SMA_20.')

def parse_strategy(source):
    rules = {}
    for lineno, line in enumerate(source.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.fullmatch(r'(BUY|SELL)\s+IF\s+(.+)', line, re.I)
        if not m:
            raise StrategyError(f'Line {lineno}: expected BUY IF ... or SELL IF ...')
        action = m.group(1).upper()
        if action in rules:
            raise StrategyError(f'Line {lineno}: duplicate {action} rule')
        try:
            rules[action] = Parser(m.group(2)).parse()
        except StrategyError as e:
            raise StrategyError(f'Line {lineno}: {e}') from e
    if set(rules) != {'BUY', 'SELL'}:
        raise StrategyError('Provide exactly one BUY IF rule and one SELL IF rule')
    return rules

def needed_fields(node):
    if node.op == 'FIELD':
        return {node.a}
    if node.op == 'CONST':
        return set()
    return needed_fields(node.a) | (needed_fields(node.b) if node.b else set())

def evaluate(node, values):
    op = node.op
    if op == 'CONST': return node.a
    if op == 'FIELD': return values[node.a]
    if op == 'NOT': return not evaluate(node.a, values)
    if op == 'AND': return bool(evaluate(node.a, values)) and bool(evaluate(node.b, values))
    if op == 'OR': return bool(evaluate(node.a, values)) or bool(evaluate(node.b, values))
    a, b = evaluate(node.a, values), evaluate(node.b, values)
    if a is None or b is None: return False
    return {'<': lambda: a < b, '>': lambda: a > b, '<=': lambda: a <= b,
            '>=': lambda: a >= b, '==': lambda: a == b, '!=': lambda: a != b}[op]()
