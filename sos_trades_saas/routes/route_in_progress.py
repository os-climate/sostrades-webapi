import time

from flask import make_response, jsonify
from werkzeug.exceptions import abort

from sos_trades_api.base_server import app
from sos_trades_api.controllers.sostrades_data.calculation_controller import calculation_status
from sos_trades_api.controllers.sostrades_main.study_case_controller import load_study_case, light_load_study_case
from sos_trades_api.controllers.sostrades_post_processing.post_processing_controller import \
    load_post_processing_graph_filters, load_post_processing
from sos_trades_api.models.database_models import StudyCaseExecution
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess
from sos_trades_core.tools.post_processing.post_processing_bundle import PostProcessingBundle
from sos_trades_core.tools.post_processing.post_processing_factory import PostProcessingFactory
from sos_trades_saas.tools.credentials import restricted_viewer_required


@app.route(f'/saas/load/postprocess/<int:study_id>', methods=['GET'])
@auth_required
@restricted_viewer_required
def load_post_process(study_id: int):
    try:

        user = get_authenticated_user()
        study_case_access = StudyCaseAccess(user.id)
        study_access_right = study_case_access.get_user_right_for_study(study_id)

        study_manager = light_load_study_case(study_id)
        post_processing_factory = PostProcessingFactory()

        all_post_processings_bundle = post_processing_factory.get_all_post_processings(
            study_manager.execution_engine,
            filters_only=True)
        print(all_post_processings_bundle)
        all_post_processings_bundle = post_processing_factory.get_all_post_processings(
            study_manager.execution_engine,
            filters_only=False)
        print(all_post_processings_bundle)

        return make_response(jsonify(all_post_processings_bundle), 200)

    except Exception as e:
        abort(400, str(e))
