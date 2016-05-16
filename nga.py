#!/usr/bin/env python

# Nga
# Copyright (c) 2010 - 2016, Charles Childers
# Copyright (c) 2011 Greg Copeland ( optimizations and process() rewrite )
# Copyright (c) 2012 Michal J Wallace ( --dump )
# -----------------------------------------------------------------------------

import os, sys, math, struct
from struct import pack, unpack

set_termio = False
try:
    import termios
    set_termio = True
except: pass

EXIT = 0x0FFFFFFF # preliminary value

# -----------------------------------------------------------------------------
def rxDivMod( a, b ):
  x = abs(a)
  y = abs(b)
  q, r = divmod(x, y)

  if a < 0 and b < 0:
    r *= -1
  elif a > 0 and b < 0:
    q *= -1
  elif a < 0 and b > 0:
    r *= -1
    q *= -1

  return q, r

# -----------------------------------------------------------------------------
def process( memory ):
  ip = 0
  global EXIT
  EXIT = len( memory )
  stack = [] * 128
  address = [] * 1024
  opcode = 0

  while ip < EXIT:
    print('A opcode', opcode, 'ip', ip, 'stack', stack, 'adr', address)
    opcode = memory[ip]
    print('B opcode', opcode, 'ip', ip, 'stack', stack, 'adr', address)
    if opcode >= 0 and opcode <= 26:

      if   opcode ==  0:   # nop
        pass

      elif opcode ==  1:   # lit
        ip += 1
        stack.append( memory[ip] )

      elif opcode ==  2:   # dup
        stack.append( stack[-1] )

      elif opcode ==  3:   # drop
        stack.pop()

      elif opcode ==  4:   # swap
        a = stack[-2]
        stack[-2] = stack[-1]
        stack[-1] = a

      elif opcode ==  5:   # push
        address.append( stack.pop() )

      elif opcode ==  6:   # pop
        stack.append( address.pop() )

      elif opcode ==  7:   # jump
        a = stack.pop()
        ip = a - 1

      elif opcode ==  8:   # call
        address.append( ip )
        ip = stack.pop() - 1

      elif opcode ==  9:   # if
        f = stack_pop()
        t = stack_pop()
        v = stack_pop()
        if v != 0:
          address.append( ip )
          ip = t - 1
        else:
          address.append( ip )
          ip = f - 1

      elif opcode ==  10:  # return
        ip = address.pop()

      elif opcode == 11:   # EQ
        a = stack.pop()
        b = stack.pop()
        if b == a:
          stack.append( -1 )
        else:
          stack.append( 0 )

      elif opcode == 12:   # -EQ
        a = stack.pop()
        b = stack.pop()
        if b != a:
          stack.append( -1 )
        else:
          stack.append( 0 )

      elif opcode == 13:   # LT
        a = stack.pop()
        b = stack.pop()
        if b < a:
          stack.append( -1 )
        else:
          stack.append( 0 )

      elif opcode == 14:   # GT
        a = stack.pop()
        b = stack.pop()
        if b > a:
          stack.append( -1 )
        else:
          stack.append( 0 )

      elif opcode == 15:   # @
        stack[-1] = memory[stack[-1]]

      elif opcode == 16:   # !
        mi = stack.pop()
        memory[mi] = stack.pop()

      elif opcode == 17:   # +
        t = stack.pop()
        stack[ -1 ] += t
        stack[-1] = unpack('=l', pack('=L', stack[-1] & 0xffffffff))[0]

      elif opcode == 18:   # -
        t = stack.pop()
        stack[-1] -= t
        stack[-1] = unpack('=l', pack('=L', stack[-1] & 0xffffffff))[0]

      elif opcode == 19:   # *
        t = stack.pop()
        stack[-1] *= t
        stack[-1] = unpack('=l', pack('=L', stack[-1] & 0xffffffff))[0]

      elif opcode == 20:   # /mod
        a = stack[-1]
        b = stack[-2]
        stack[-1], stack[-2] = rxDivMod( b, a )
        stack[-1] = unpack('=l', pack('=L', stack[-1] & 0xffffffff))[0]
        stack[-2] = unpack('=l', pack('=L', stack[-2] & 0xffffffff))[0]

      elif opcode == 21:   # and
        t = stack.pop()
        stack[-1] &= t

      elif opcode == 22:   # or
        t = stack.pop()
        stack[-1] |= t

      elif opcode == 23:   # xor
        t = stack.pop()
        stack[-1] ^= t

      elif opcode == 24:   # shift
        a = stack.pop()
        b = stack_pop()
        if a < 0:
          stack.append( b << (a * -1) )
        else:
          stack.append( b >> a )

      elif opcode == 25:   # 0;
        if stack[-1] == 0:
          stack.pop()
          ip = address.pop()

      elif opcode == 26:   # end
        print('end')
        print(stack)
        ip = EXIT

    ip += 1
  return stack, address, memory


def dump( stack, address, memory ):
  """
  dumps the vm state. for use with /test/ngarotest.py
  triggered when --dump passed to the program.
  """
  fsep = chr( 28 ) # file separator
  gsep = chr( 29 ) # group separator
  sys.stdout.write( fsep )
  sys.stdout.write( ' '.join( map( str, stack )))
  sys.stdout.write( gsep )
  sys.stdout.write( ' '.join( map( str, address )))
  sys.stdout.write( gsep )
  sys.stdout.write( ' '.join( map( str, memory )))


# -----------------------------------------------------------------------------
def run():

  imgpath = None
  dump_after = False

  i = 1 # sys.argv[0] is 'nga.py', okay to skip
  while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == "--dump":
      dump_after = True
    elif arg == "--image":
      i += 1
      arg = sys.argv[i]
      if os.path.exists(arg): imgpath = arg
    else:
      print("file not found: %r" % arg)
      sys.exit(-2)
    i += 1
  del i
  imgpath = imgpath or 'ngaImage'

  # print "imgpath:", imgpath
  cells = int(os.path.getsize(imgpath) / 4)
  f = open( imgpath, 'rb' )
  memory = list(struct.unpack( cells * 'i', f.read() ))
  f.close()

  if not dump_after:
    remaining = 1000000 - cells
    memory.extend( [0] * remaining )

  global set_termio
  if set_termio:
    try: old = termios.tcgetattr(sys.stdin.fileno())
    except: set_termio = False
  if set_termio:
    t = termios.tcgetattr(sys.stdin.fileno())
    t[3] = t[3] & ~(termios.ICANON | termios.ECHO | termios.ISIG)
    t[0] = 0
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, t)
  try:
    stack, address, memory = process(memory)
    if dump_after: dump(stack, address, memory)
  except:
    raise
  finally:
    if set_termio:
      termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, old)

# -----------------------------------------------------------------------------
if __name__ == "__main__":
  run()