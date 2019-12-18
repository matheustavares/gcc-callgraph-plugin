#include <stdlib.h>
#include <math.h>
#include "sort.h"

#define MAX_SWAPS_IN_A_ROW 10

int random_in_range(int max)
{
	return (int) floorf((rand() / (float) RAND_MAX) * max);
}

int random_boolean()
{
	return (rand() > RAND_MAX / 2);
}

void random_swap_two(double *arr, int N)
{
	int a = random_in_range(N);
	int b = random_in_range(N);
	double tmp = arr[a];
	arr[a] = arr[b];
	arr[b] = tmp;
}

void random_swap_random(double *arr, int N)
{
	int swaps = random_in_range(MAX_SWAPS_IN_A_ROW) / 2;
	for (int i = 0; i < swaps; ++i)
		random_swap_two(arr, N);
}

void random_sort(double *arr, int N)
{
	while (!is_sorted(arr, N)) {
		if (random_boolean())
			random_swap_random(arr, N);
		else
			random_swap_two(arr, N);
	}
}

int is_sorted(double *arr, int N)
{
	if (N == 1)
		return 1;

	for (int i = 1; i < N; ++i)
		if (arr[i] < arr[i-1])
			return 0;
	return 1;
}
