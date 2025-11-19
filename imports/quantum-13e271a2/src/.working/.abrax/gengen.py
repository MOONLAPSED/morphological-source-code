class Generator:

    def __init__(self, start_date, end_date, between_time=None, freq='D', filter_func=lambda df: df):
        """
        Creates a new time series generator using the specified events. The names of the events will be used
        later to name the columns of generated DataFrames.

        :param start_date: The first date of the series to generate.
        :param end_date: The last date of the series to generate.
        :param between_time A pair which, when specified, define a start and end times for every day generated
        :param freq: The frequency to be used, in terms of Pandas frequency strings.
        :param filter_func: A filter function to apply to the generated data before returning.
        """
        self.between_time = between_time
        self.freq = freq
        self.filter_func = filter_func
        self.start_date = start_date
        self.end_date = end_date

    def generate(self, events, n=1, new_start_date=None, new_end_date=None):
        """
        Generates time series from the model assigned to the present generator.

        :param events: Either a list of events or a dict of events. In the former case, the name of each
        event is retrieved from the event itself. In the latter case, the user can specify new names.
        :param n: The number of series to generate.
        :param new_start_date: If specified, overrides the class' start_date for this particular generation.
        :param new_end_date: If specified, overrides the class' end_date for this particular generation.

        :return: A list of generated time series.
        """

        #
        # Setup events to use
        #
        self._set_events(events)

        # calculate proper start data
        if new_start_date is not None:
            start = new_start_date
        else:
            start = self.start_date

        # calculate proper end date
        if new_end_date is not None:
            end = new_end_date
        else:
            end = self.end_date


        #
        # Generate data from the given events.
        #
        generated_data = []
        for i in range(0, n):
            values = {}
            dates = pd.date_range(start, end, freq=self.freq)
            for name in self.named_events:
                self.named_events[name].reset()  # clears the cache

            for t in dates:
                for name in self.named_events:
                    if name not in values:
                        values[name] = []

                    values[name].append(self.named_events[name].execute(t))

            df = pd.DataFrame(values, index=dates)
            if self.between_time is not None:
                df = df.between_time(self.between_time[0], self.between_time[1])

            df = self.filter_func(df)
            generated_data.append(df)

        if len(generated_data) > 1:
            return generated_data
        else:
            return generated_data[0]

    def _set_events(self, events):
        if isinstance(events, dict):
            self.named_events = events
        else:
            self.named_events = {}

            # make iterable
            if not isinstance(events, list):
                events = [events]

            for i, event in enumerate(events):
                if event.name is not None:
                    self.named_events[event.name] = event
                else:
                    self.named_events['Event ' + str(i)] = event


def generate(model, start_date, end_date, n=1, freq='D', filter_func=lambda df: df):
    """
    A convenience method to generate time series from the specified model using the default generator.

    :param model: The model from which the data is to be generated.
    :param start_date: The first date of the series to generate.
    :param end_date: The last date of the series to generate.
    :param n: The number of series to generate.
    :param freq: The frequency to be used, in terms of Pandas frequency strings.
    :param filter_func: A filter function to apply to the generated data before returning.

    :return: A list of generated time series.
    """
    data = Generator(start_date=start_date,
                     end_date=end_date,
                     freq=freq,
                     filter_func=filter_func) \
        .generate(model, n=n)

    return data

def generate_and_plot(model, start_date, end_date, n=1, freq='D', return_data=False, filter_func=lambda df: df,
                      grid=True):
    """
     A convenience method to generate time series from the specified model using the default generator, and also plot
     them.

     :param model: The model from which the data is to be generated.
     :param start_date: The first date of the series to generate.
     :param end_date: The last date of the series to generate.
     :param n: The number of series to generate.
     :param freq: The frequency to be used, in terms of Pandas frequency strings.
     :param return_data: Whether to return the generated data or not. The default is False, useful when
                         usin Jupyter notebooks only to show the charts, without further data processing.
     :param filter_func: A filter function to apply to the generated data before returning.

     :return: A list of generated time series.
     """
    data = generate(model, start_date, end_date, n=n, freq=freq, filter_func=filter_func)

    # plot
    def aux_plot(df):
        df.plot(grid=grid)

    for i in range(0, n):
        aux_plot(data[i]) if n > 1 else aux_plot(data)
        plt.show()

    if return_data:
        return data

def save_to_csv(data, common_name, **kwargs):
    for i, df in enumerate(data):
        name = common_name + '_' + i
        df.to_csv(name, kwargs)