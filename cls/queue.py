class Queue:
    def __init__(self):
        self.items = []
        self.pointer = 0

    def empty(self):
        return self.items == []

    def enqueue(self, item):
        self.items.append(item)

    def dequeue(self):
        self.items.pop(-1)

    def pop(self, idx):
        return self.items.pop(idx)

    def size(self):
        return len(self.items)

    def print_queue(self):
        for item in self.items:
            print(item)

    def clear(self):
        self.items = []

    def __iter__(self):
        return self

    def __next__(self):
        if self.pointer > len(self.items) - 1:
            self.pointer = 0
            raise StopIteration
        item = self.items[self.pointer]
        self.pointer += 1
        return item
