import random

num=random.randint(1, 10)

num=num%2

print(num)
print("\n")
if num == 0:
	print("bet to bull, rise")
else:
	print("bet to bear, down")



