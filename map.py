"""Map reduce job definitions."""

import mapreduce

import model


class FakeSliceContext(object):
    """Imitates mapreduce.api.map_job.map_job_context.SliceContext just enough
    to run simple previews of a mapper."""
    def __init__(self, job_context):
        self.job_context = job_context


def get_fake_context(job_config):
    """Gives a context sufficient to run a preview of mapper functionality."""
    job_context = mapreduce.api.map_job.map_job_context.JobContext(job_config)
    return FakeSliceContext(job_context)


# If this class structure (with the __call__) looks funny to you, read on:
# It's just a function-generator. When you instantiate the class, you get a
# callable object, which you can treat just like a function.
# Example:
# f = LowerCaseLoginMapper()
# f(context, entity)  # yields a db operation

# For unit testing, you can call the do method and get the changed entity,
# rather than an operation.
# Example:
# f = LowerCaseLoginMapper()
# changed_entity = f.do(context, original_entity)

class TagChangeMapper(mapreduce.api.map_job.mapper.Mapper):
    def __call__(self, context, practice):
        """Re-arranges how tags are stored in properties.

        Must be idempotent!

        Args:
            context: map_job_context.JobContext, contains (among other things),
                parameters provided to the input reader.
            practice: model.Practice, the practice that needs its tags fixed.
        """
        practice = self.do(context, practice)
        # Yielding an operation, rather the saving to the db here, allows
        # the map reduce framework to batch them all together efficiently.
        yield mapreduce.operation.db.Put(practice)

    def do(self, context, practice):
        """Separation from db operation allows unit testing."""
        practice.tags = (practice.mindset_tags + practice.practice_tags)
        # Pending further discussion, we are dropping the information in
        # these properties, so they are commented out.
        # practice.tags.append(practice.time_of_year)
        # practice.tags.append(practice.class_period)
        return practice

    def launch(self, preview_only=False):
        """Launch a map reduce job to re-arrange tags in a practice.

        Args:
            preview_only: bool, default False, if True does not launch job,
                only returns the configuration for the potential job.
        """
        job_config = mapreduce.api.map_job.JobConfig(
            # How the job will be listed on the control panel at /mapreduce.
            job_name='tag_change',
            # The "function" that will process each entity.
            mapper=TagChangeMapper,
            # The way data will be read into the mapper. This one just iterates
            # over every entity of a given kind, providing the entity to the
            # mapper.
            input_reader_cls=mapreduce.input_readers.DatastoreInputReader,
            input_reader_params={
                'entity_kind': 'model.Practice'
                # 'filters': [('deleted', '=', False)],
            },
            # There are no output writers or reduce steps since this job is so
            # simple.
            # The only thing left is to point to the config for the task queue this
            # job will use.
            queue_name='default')

        if not preview_only:
            mapreduce.api.map_job.Job.submit(job_config)

        return job_config
