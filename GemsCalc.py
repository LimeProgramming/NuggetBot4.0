
x = 50
t = 0

for i in range(1, 101, 1):

    if i%10 == 0:
        x = round(x + (x * 0.3))

    elif i%5 == 0:
        x = round(x + (x * 0.2))
    


    #if i%10 == 0:
    #    x = round(x + (x * 0.5))

    #t = t + x
    
    #print(f'{i},{x}')
    #print(f'Level: {i},\tGems: {x},\ttotal: {t}')


    #print(f'{i},{x}')
    #x = round(x + (x * 0.05))


    print(f'WHEN level = {i} THEN reward = {x};')
