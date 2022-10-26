'''
Copyright 2022 Airbus SAS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
#!/usr/bin/python

import sys
from importlib import import_module
from sos_trades_api.models.database_models import ReferenceStudy
from sos_trades_api.server.base_server import db, app
from sos_trades_api.config import Config
with app.app_context():

    ref_model_id = int(sys.argv[2])
    ref_gen_model = ReferenceStudy.query.filter(ReferenceStudy.id == ref_model_id).update({
        'execution_status': ReferenceStudy.RUNNING})
    db.session.commit()
    # reference_basepath = sys.argv[3]  # Config().reference_root_dir
    reference_basepath = Config().reference_root_dir
    # Retrieve module to import

    module_name = sys.argv[1]
    try:
        imported_module = import_module(module_name)
        imported_usecase = getattr(imported_module, 'Study')()
        try:
            imported_usecase.set_dump_directory(reference_basepath)
            imported_usecase.run(dump_study=True)
        except:
            pass
        ref_gen_model = ReferenceStudy.query.filter(ReferenceStudy.id == ref_model_id).update({
            'execution_status': ReferenceStudy.FINISHED})
        db.session.commit()
    except Exception as e:
        ref_gen_model = ReferenceStudy.query.filter(ReferenceStudy.id == ref_model_id).update(
            {'execution_status': ReferenceStudy.FAILED, 'generation_logs': e})
        db.session.commit()
