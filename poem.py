#!/usr/bin/python
# -*- coding: utf-8 -*-

#TODO: use espeak, add pitch to "sing" the poems

class Poem(object):
  syllable_structure = None
  rhyme_scheme = None
  lines_needed = None
  lines = []
  def get_format(self):
    format = {}
    if self.rhyme_scheme:
      format["rhyme_scheme"] = self.rhyme_scheme
    if self.lines_needed:
      format["lines_needed"] = self.lines_needed
    if self.syllable_structure:
      format["syllable_structure"] = self.syllable_structure
    return format

  def sing(self):
    raise NotYetImplementedError

class Haiku(Poem):
  syllable_structure = [5,7,5]
  rhyme_scheme = "abc"

class FreeVerse(Poem):
  def __init__(self, lines_needed=10):
    self.lines_needed = lines_needed

class Limerick(Poem):
  syllable_structure = [(9,11),(9, 11),6,6,(9, 11)]
  rhyme_scheme = "aabba"

class Sonnet(Poem):
  syllable_structure = [10]
  rhyme_scheme = "ababcdcdefefgg"

class NotYetImplementedError(Exception):
  pass
