#!/usr/bin/python
# -*- coding: utf-8 -*-

from rhymetime import RhymeChecker
from random import randint, shuffle
import re
import sys
import poem
from line import Line

debug_lines = ["camping is in tents", "my tree table tries", "between those times I slept none"]

"""
Architecture:
  1. For each validation type (e.g. syllable count, rhyming, eventually stress), create a "hash" dicts.
    a. Each dict is of the form: hash_value -> [line1, line2, line3]
    b. each hash_value is computed by hash(line) where the syllable_hash function returns syllable length of the line and rhyme_hash returns the rime (i.e. nucleus + coda) of the final syllable of the line.
  2. Discard or ignore all syllable_hash_dict entries whose syllable counts are not in the format.
  3: Optionally, pair stuff, e.g. rhyming pairs or triplets (or n-lets where n is the greatest amount of rhyming lines needed in the format, e.g. 3 for a limerick, , but only 2 for a sonnet.) and, if necessary, of the right syllable length.
  4. From these pairs, assemble a poem.

  e.g. python poemifier.py sonnet ./SCALIA.txt 
"""

#TODO: make a Heroku/Flask-based app for people to make their own poems.

class Poemifier:
  def __init__(self, poem):
    """Specify the name of a known format or specify a fully-defined format."""
    self.debug = False
    #self.poem_complete = False #dunno what this is.
    #self.poem_validator = PoemValidator()

    self.format = poem.get_format()
    self.lines_needed = self.format["lines_needed"]

    self.rhyme_checker = RhymeChecker()
    self.rhyme_checker.debug = False

    self.allow_partial_lines = False
    self.where_to_put_partial_lines = {}
    self.asdf = {}

    #TODO abstract away hash types by format.
    self.rhyme_dict = {}
    self.syllable_count_dict = {}
    # self.global_only_once = 100

  def try_line(self, line):
    """ Add a line, then return True if, given that line, a poem can be created."""
    self.add_line(line)
    return self.create_poem() #False or a poem.

  def add_line(self, line):
    """
    Adds a line to the format hash dicts. Return False if the line cannot be used.
    """
    #TODO: abstract away format stuff
    # format_items = [[self._rime, self.rhyme_dict], [self._syllable_count, self.syllable_count_dict]]
    # for hashFunc, format_hash_dict in format_items:
    splits = []

    #TODO: if self.allow_partial_lines, copy the shit from an older version in Git
    #      to keep the old way of doing things
    if not self.allow_partial_lines:
      for index, syllable_count_token in enumerate(self.format["syllable_structure"]):
        rest_of_syllables = self.format["syllable_structure"][index:] #inclusive
        temp_splits = line.split_line_to_format(rest_of_syllables)
        if temp_splits != False:
          self.asdf[line] = self.asdf.get(line, []) + [index]
          splits += temp_splits
      #print splits
    else:
      raise YourHandsUpInTheAirTonight
      #this bit is left over, totally wrong.
      #it needs to add correctly-split versions (at each token) for all parts of the sentence
      #right now it just correctly splits the first N syllables of the sentences for each token
      for syllable_count_token in self.format["unique_syllable_structure"]:
        splits += line.split_line_at_syllable_count(syllable_count_token)

    for split in splits:
      #TODO: figure out a way to pair these lines, so we don't get stuff split in the middle.
      # alternatively, find a way to "tentatively" add the lines and remove them immediately if the split lines aren't kosher.
      if self.allow_partial_lines:
        for part_of_line in split:
          self._add_line_helper(part_of_line)
      else:
        #if partial lines aren't allowed, don't bother adding non-beginning parts of partial lines to the hashes.
        self._add_line_helper(split[0])
    return self._add_line_helper(line)

  def _add_line_helper(self, line):
    syll_count = line.syllable_count()
    if syll_count in self.format["syllable_count_to_syllable_count_token"].keys(): #TODO: obviously, abstract this.
      rime = line.rime()
      if not rime:
        return False
      rime = tuple(rime)
      for syll_count_token in self.format["syllable_count_to_syllable_count_token"][syll_count]:
        if syll_count_token not in self.syllable_count_dict:
          self.syllable_count_dict[syll_count_token] = []
        self.syllable_count_dict[syll_count_token].append(line)

        if rime not in self.rhyme_dict:
          self.rhyme_dict[rime] = {}
        if syll_count_token not in self.rhyme_dict[rime]:
          self.rhyme_dict[rime][syll_count_token] = []
        self.rhyme_dict[rime][syll_count_token].append(line)
      return True
    else:
      return False

  def validate_rhyme(self, poem, line, index):
    """True if this line fits in the rhyme scheme where it is."""
    temp_poem = list(poem) #"copy" the list
    temp_poem[index] = line

    last_word = line.split(" ")[-1]
    last_word.strip(".,?!:;\" ")
    #does it fit where it is.
    rhyme_symbol = self.format["rhyme_scheme"][index]
    lines_to_compare_to = [temp_poem[i] for i, symbol in enumerate(self.format["rhyme_scheme"]) if symbol == rhyme_symbol and temp_poem[i] and i != index]
    if not lines_to_compare_to:
      if self.debug:
        print "nothing to compare " + last_word + " to. " 
      return True
    words_to_compare_to = map(lambda x: x.split(" ")[-1], lines_to_compare_to )
    return True in map(lambda x: self.rhyme_checker.rhymes_with(last_word, x), words_to_compare_to)

  def _group_lines_by_rime(self):
    """Group lines with the same syllable count and then by rime."""
    #all the lines in any of the dicts are guaranteed to be of acceptable length.
    #groups = {6 => {"EH" => ["a", "b", "c"], "OI" => ...}, (9,11) => { "AH" => ["a", "b", "c"] "UH" => ...}, }

    groups_by_rhyme = {}
    groups_by_syll_count = {}
    for rime, rhyme_groups in self.rhyme_dict.items():
      #skip rhyme dict entries with only one element, unless there are unrhyming elements in the rhyme scheme
      if len(rhyme_groups) == 1 and len(rhyme_groups.values()[0]) == 1 and \
            not filter(lambda item: self.format["rhyme_scheme"].count(item) == 1, list(self.format["rhyme_scheme"])):
        #print("skipping something while grouping")
        continue
      inner_groups_by_syll_count = {}
      for syllable_count_token, rhyme_group in rhyme_groups.items():
        #exclude words from the rhyme group whose last word is the last word of another line in this rhyme group
        already_used_last_words = set()
        new_rhyme_group = []
        for rhyme_line in rhyme_group:
          if rhyme_line.clean_text().split(" ")[-1].lower() not in already_used_last_words or \
            self.format["syllable_structure"].count(syllable_count_token) == 1:
            already_used_last_words.add(rhyme_line.clean_text().split(" ")[-1].lower())
            new_rhyme_group.append(rhyme_line)

        inner_groups_by_syll_count[syllable_count_token] = new_rhyme_group
        if syllable_count_token not in groups_by_syll_count.keys():
          groups_by_syll_count[syllable_count_token] = {}
        groups_by_syll_count[syllable_count_token][rime] = new_rhyme_group
      groups_by_rhyme[rime] = inner_groups_by_syll_count
    return groups_by_syll_count

  def _prune_too_small_grouped_lines(self, groups):
    """ Remove rimes with too few members, in place.

      The returned dict contains only lines that are eligible to appear in the poem.
      A rime_group has too few members iff:
        1. Its count of members is less than the number
    """
    #groups = {}
    min_rime_count = min(list(set(map(lambda x: self.format["rhyme_scheme"].count(x), self.format["rhyme_scheme"] ))))
    for syllcount, syllcount_group in groups.items():
      #groups[syllcount] = {}
      for rime, rime_group in syllcount_group.items():
        if len(rime_group) >= min(self.format["syllable_structure"].count(syllcount), min_rime_count):
          #groups[syllcount][rime] = rime_group
          continue
        else:
          del groups[syllcount][rime]
      if len(syllcount_group) == 0:
        del groups[syllcount]

  def _prune_desiblinged_lines_from_groups(self, groups):
    """filter out partial-lines whose siblings aren't in `groups`, in place"""

    #TODO:
    #for each partial-line, figure out what order of syllable and rhyme structures would be needed to slot it into the poem
    #e.g. it's got two pieces that rhyme of 9-11 syllables each
    #remove those partial lines who can't fit anywhere. don't accept the partial line if it's picked where it can't fit.
    #slot in the partial line and everything after if it can.

    flat_list_of_kosher_lines = [lines for lines in groups.items()]
    for syllcount, syllcount_group in groups.items():
      #groups[syllcount] = {}
      for rime, rime_group in syllcount_group.items():
        for line in rime_group:
          if not line.is_partial():
            continue
          else:
            #TODO: abstract this bit.
            size = line.total_siblings() + 1 #+1 for the line itself.
            format_items = zip(self.format["rhyme_scheme"], self.format["syllable_structure"])
            sequential_format_orderings = [] 
            for i in range(0, (len(format_items) - size + 1)):
              sequential_format_orderings.append(format_items[i:i+size])
            okay = []

            for subformat in sequential_format_orderings:
              okay.append(True)
              mini_rhyme_rime_map = {} # 'a' => "EH" etc
              all_lines = [line] + line.after_siblings()
              for i, sibling_line in enumerate(all_lines):
                if not okay[-1]: #don't waste our time
                  continue

                rhyme_symbol = subformat[i][0]
                needed_syllable_count = subformat[i][1]
                #TODO: abstract this away.

                #test syllable count
                if isinstance(needed_syllable_count, int):
                  if sibling_line.syllable_count() != needed_syllable_count:
                    okay[-1] = False
                    #print "failed on syllable count " + str(needed_syllable_count)
                    break
                elif isinstance(needed_syllable_count, tuple):
                  if not (sibling_line.syllable_count() >= needed_syllable_count[0] and sibling_line.syllable_count() <= needed_syllable_count[1]):
                    okay[-1] = False
                    #print "failed on syllable count " + str(needed_syllable_count)
                    break

                #test rhyme
                if rhyme_symbol in mini_rhyme_rime_map:
                  #TODO: compare only the last N syllables in rime for N = min(len(rime1, rime2))
                  min_rime_size = min( len(mini_rhyme_rime_map[rhyme_symbol]), len(sibling_line.rime()))
                  if mini_rhyme_rime_map[rhyme_symbol][-min_rime_size:] != sibling_line.rime()[-min_rime_size]:
                    okay[-1] = False
                    print "failed on rhyme"
                    break
                else:
                  mini_rhyme_rime_map[rhyme_symbol] = tuple(sibling_line.rime()) if sibling_line.rime() else False

            if True not in okay:
              rime_group.remove(line)
            else:
              self.where_to_put_partial_lines[line] = [i for i, b in enumerate(okay) if b]
              #store where it's okay.

            #TODO: does this line and its sibling fit one of the formats in sequential_format_orderings ?

            # # all_siblings_survive = True
            # # for sibling in line.before_siblings():
            # #   all_siblings_survive = all_siblings_survive and sibling in flat_list_of_kosher_lines
            # # for sibling in line.after_siblings():
            # #   all_siblings_survive = all_siblings_survive and sibling in flat_list_of_kosher_lines
            # # if not all_siblings_survive:
            # #   rime_group.remove(line)

  # def _cull_desiblinged_lines_from_poems(self, poems):
  #   """ Remove those poems that contain a split line without its siblings."""
  #   new_poems = []
  #   for poem in poems:
  #     valid = True
  #     for index, line in enumerate(poem):
  #       if line.is_partial() and line.next_sibling():
  #         if len(poem) == (index + 1) or line.next_sibling() != poem[index + 1]:
  #           valid = False
  #       if line.is_partial() and line.prev_sibling():
  #         if index == 0 or line.prev_sibling() != poem[index - 1]:
  #           valid = False
  #     if valid:
  #       new_poems.append(poem)
  #   return new_poems

  def _shuffle_grouped_lines(self, groups):
    for syllcount, syllcount_group in groups.items():
      for rime, rime_group in syllcount_group.items():
        shuffle(rime_group)

  def create_poem(self, be_random=False):
    """ Return False or a poem. """
    #TODO: again, abstraction!
    poem = [None] * self.format["lines_needed"]
    if self.format["rhyme_scheme"]:
                          #old debug stuff: why is a haiku not being genreated?
                          # flat_lines = [item.text for subl2 in [item for sublist in [d.values() for d in self.rhyme_dict.values()] for item in sublist] for item in subl2]
                          # print [debug_line in flat_lines for debug_line in debug_lines]
      groups = self._group_lines_by_rime()
                          # seven = [item for sublist in groups[7].values() for item in sublist]
                          # print "seven: " + str([debug_line in seven for debug_line in debug_lines])
                          # print groups[7][(('AH', 'N'),)]

                          # flat_lines = [item.text for subl2 in [item for sublist in [d.values() for d in groups.values()] for item in sublist] for item in subl2]
                          # print [debug_line in flat_lines for debug_line in debug_lines]

      self._prune_too_small_grouped_lines(groups)
      if not self.allow_partial_lines:
        # print "before: " + str(len(groups.get(5, "")))
        # print "before: " + str(len(groups.get(5, "")))
        self._prune_desiblinged_lines_from_groups(groups)
        self._prune_too_small_grouped_lines(groups)
        # print "after, 5: " + str(len(groups.get(5, "")))
        # print "after, 7: " + str(len(groups.get(7, "")))
        # print "7: " + str(groups.get(7, ""))
        # print ""

      unique_rhyme_scheme = set(list(self.format["rhyme_scheme"]))
      for rhyme_element in unique_rhyme_scheme:
        unique_syllable_structure = list(self.format["unique_syllable_structure"])
        shuffle(unique_syllable_structure)
        for syllable_count_token in unique_syllable_structure:
          if syllable_count_token not in groups:
            continue

          candidate_lines = groups[syllable_count_token].values()
          if be_random:
            shuffle(candidate_lines)

          # print "candidate lines: %(c)s" % {'c' : candidate_lines}

          if not candidate_lines:
            continue
 
          #TODO:
          #for each set of lines in candidate lines, check if it has any partial lines
          #and if so, whether, the following/preceding line(s) fit in the next slot.
          #throw it out if not.

          #for each syllable in the candidate lines for this syllable_count_token, create a poem
          for this_sylls_lines in candidate_lines:
            for index, syllable_count in enumerate(self.format["syllable_structure"]):
              if syllable_count == syllable_count_token and rhyme_element == self.format["rhyme_scheme"][index]:
                for next_line in this_sylls_lines:
                  if not poem[index] and next_line not in poem: #ensures there are no duplicate lines in poems.
                    if (not self.allow_partial_lines) and next_line.is_partial():
                      if next_line in self.where_to_put_partial_lines:
                        if index in self.where_to_put_partial_lines[next_line]:
                          # print "line " + str(index) + " is partial and acceptable"
                          poem[index] = next_line
                          for j, sibling in enumerate(next_line.after_siblings()):
                            #these can be depended on to fit the right syllable structure
                            poem[j + 1 + index] = sibling
                            # print "slotted in a sibling to line #%(i)s" % {'i': j + index}
                      #   else:
                      #     print "line %(l)s doesn't fit in line %(n)s" % {'l' : next_line, 'n' : index}
                      # else:
                      #   if next_line.text != "":
                      #     print str(next_line) + " didn't make it"
                    else:
                      # print "line " + str(index) + " partial? " + str(next_line.is_partial())
                      poem[index] = next_line
                      continue
                  # else:
                  #   if poem[index]:
                  #     print "skipping because line is already filled"
                  #   if next_line in poem: 
                  #     print "skipping because next_line already in poem"
                  #   print ""
              # else:
              #   pass
                # print "skipped %(l)s due to syllable/rhyme problems" % {'l' : this_sylls_lines}
                # print "syllable_count: %(sc)s , syllable_count_token: %(sct)s" % {'sc': syllable_count, 'sct': syllable_count_token}
                # print "rhyme_element: %(sc)s , self.format[rhyme_scheme][index]: %(sct)s" % {'sc': rhyme_element, 'sct': self.format["rhyme_scheme"][index]}
                # print ""
      # if not self.allow_partial_lines:
      #   print "generated " + str(len(poems)) + " semivalid poems"
      #   poems = self._cull_desiblinged_lines_from_poems(poems)
      #print "generated " + str(len(poems)) + " valid poems"

      return poem

      """
      #for each line (a combination of syllable count and rhyme -- for now (needs abstraction))
      #randomly pick an eligible line from the dicts
      #if the line picked has an after siblings, put it next if they fit, otherwise "rewind".
      #look ahead only once.
      #oppa linkedlist style
      first_in_first = groups[groups[groups.keys[0]].keys[0]][0]
      if random:
        first_in_first = groups[groups[groups.keys[0]].keys[0]][0]
        self._shuffle_grouped_lines(groups)
        print "should often differ: '" + groups[groups[groups.keys[0]].keys[0]][0] + "' ; '" + "'"

      rhyme_rime_mapping = {} #maps rhyme key (e.g. 'a' ) to a rime (e.g. "EH")
      for index, rhyme_key_syllable_count_token in enumerate(zip(list(self.format["rhyme_scheme"], self.format["syllable_structure"]))):
        rhyme_key, syllable_count_token = rhyme_key_syllable_count_token
        if rhyme_key in rhyme_rime_mapping:
          this_rime = rhyme_rime_mapping[rhyme_key]
        else:
          this_rime = groups[syllable_count_token].keys()[0]
          rhyme_rime_mapping[rhyme_key] = this_rime

        if index == 0 or not poem[index-1].next_sibling():
          poem[index] = groups[syllable_count_token][this_rime].pop()
        else:
          if poem[index-1].next_sibling() in groups[syllable_count_token][this_rime]
            poem[index] = poem[index-1].next_sibling()
          else:
            for i, rewind_line in enumerate(poem.reverse()):
              if poem[i] == None:
                continue
              if poem[i]
            #rewind: erase poem, rhyme_rime_mapping until last safe index
      """
      """
      unique_rhyme_scheme = set(list(self.format["rhyme_scheme"]))
      for rhyme_element in unique_rhyme_scheme:
        for syllable_count_token in self.format["unique_syllable_structure"]:
          if syllable_count_token not in groups:
            return None
          #get all the sets of rhyming lines that have at least enough rhymes to fit what we need for this syllable count.
          candidate_lines = filter(lambda rhymes: len(rhymes) >= self.format["syllable_structure"].count(syllable_count_token), 
                                    groups[syllable_count_token].values())
          if not candidate_lines:
            return None
 
          #TODO:
          #for each set of lines in candidate lines, check if it has any partial lines
          #and if so, whether, the following/preceding line(s) fit in the next slot.
          #throw it out if not.
          if random:
            shuffle(candidate_lines)
 
          this_sylls_lines = list(candidate_lines[0])
          for index, syllable_count in enumerate(self.format["syllable_structure"]):
            if syllable_count == syllable_count_token and rhyme_element == self.format["rhyme_scheme"][index]:
              for next_line in this_sylls_lines:
                if poem[index] == None and next_line not in poem: #ensures there are no duplicate lines in poems.
                  poem[index] = next_line
                  break
      return map(lambda line: line.text, poem)
      """
    # elif self.format["syllable_structure"]:
    #   #TODO: delete all the hash entries that don't fit anything in the syllable structure
    #   raise ShitsFuckedException # I think this is dead code
    #   for index, syllable_count in enumerate(self.format["syllable_structure"]):
    #     if syllable_count not in self.syllable_count_dict:
    #       return None 
    #     candidate_lines = filter(lambda l: l not in poem, self.syllable_count_dict[syllable_count])
    #     if not candidate_lines:
    #       return None
    #     if random:
    #       next_line_index = randint(0,len(candidate_lines) - 1)
    #     else:
    #       next_line_index = 0
    #     next_line = candidate_lines[next_line_index]
    #     poem[index] = next_line
    #   return poem
    # else:
    #   #there's no rhyme scheme or syllable structure.
    #   pass

def _test():
  import doctest
  doctest.testmod()

class ShitsFuckedException(Exception):
  pass



if __name__ == "__main__":
  poem = getattr(poem, sys.argv[1].capitalize())() #class
  input_text = sys.argv[2] or "./SCALIA.txt"

  lists_of_linetexts = map(lambda x: x.split(";"), open(sys.argv[2]).read().split("\n"))
  #lists_of_linetexts = map(lambda x: x.split(","), open(sys.argv[2]).read().split("\n"))

  linetexts = [line for line_list in lists_of_linetexts for line in line_list]

  #linetexts = ["camping is in tents", "my tree table tries", "between those times I slept none"]
  # linetexts = ["many words in english rhyme with song", "one two three four five six", "a bee see dee word kicks",
  #  "This is a line that is twenty long", "here are ten more ending in wrong", "Jeremy Bee Merrill plays ping pong",
  #  ]

  p = Poemifier(poem)
  p.debug = True
  #this can't be a do... while, because we have to add all the lines, then do various processing steps.
  for linetext in linetexts:
    line = Line(linetext, p.rhyme_checker)
    if line.should_be_skipped():
      continue
    #p.try_line(line) #too slow
    p.add_line(line)
  print ""
  print p.create_poem(True)

#TODO: for split lines, don't add part of the line unless we can add the rest. Use line class.
#TODO: write tests
#TODO: Allow multiple poems to be requested (only break when the number of complete poems in self.poems = the number requested)